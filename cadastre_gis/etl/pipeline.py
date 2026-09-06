"""
End-to-End Cadastral Data Ingestion & Transformation Pipeline.
Coordinates WFS parcel fetching, concurrent registry scraping, CRS transformation,
and standardized GeoJSON export.
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from cadastre_gis.config import DATA_DIR, DEFAULT_CITY_ID, DEFAULT_CITY_NAME, DEFAULT_KO_ID, MAX_WORKER_THREADS
from cadastre_gis.crs.transformer import BalkanCrsTransformer
from cadastre_gis.etl.rgurs_client import CadastreRegistryClient, parse_date_html, parse_owners_html, parse_parts_html
from cadastre_gis.etl.wfs_client import CadastreWFSClient


class CadastrePipeline:
    """
    High-speed orchestration pipeline.
    """

    def __init__(
        self,
        city_id: str = DEFAULT_CITY_ID,
        city_name: str = DEFAULT_CITY_NAME,
        ko_id: str = DEFAULT_KO_ID,
        max_workers: int = MAX_WORKER_THREADS,
        auth_key: str | None = None,
    ):
        self.city_id = city_id
        self.city_name = city_name
        self.ko_id = ko_id
        self.max_workers = max_workers

        self.wfs_client = CadastreWFSClient(auth_key=auth_key)
        self.registry_client = CadastreRegistryClient(city_id=city_id, city_name=city_name, max_connections=max_workers)
        self.transformer = BalkanCrsTransformer(source_epsg=31276, target_epsg=4326)

    def run(self, output_path: str | Path | None = None) -> dict[str, Any]:
        """
        Execute full pipeline: WFS download -> Concurrent enrichment -> CRS transform -> GeoJSON save.
        """
        out_file = Path(output_path or (DATA_DIR / f"cadastre_{self.ko_id}_wgs84.geojson"))
        out_file.parent.mkdir(parents=True, exist_ok=True)

        print(f"Step 1/3: Fetching cadastral parcels from WFS for KO={self.ko_id}...")
        wfs_data = self.wfs_client.fetch_parcels_geojson(ko_id=self.ko_id)
        features = wfs_data.get("features", [])
        total = len(features)
        print(f"  -> Fetched {total} parcels from GeoServer.")

        if total == 0:
            raise ValueError(f"No parcels found for KO {self.ko_id}. Check credentials and KO_ID.")

        # Identify unique base parcel numbers to avoid duplicate API requests
        base_to_features = {}
        for feat in features:
            props = feat.get("properties", {})
            broj = str(props.get("BROJ", "")).strip()
            if broj:
                base_to_features.setdefault(broj, []).append(feat)

        print(f"Step 2/3: Concurrently enriching {len(base_to_features)} unique base parcel bundles...")

        bundle_cache = {}

        def fetch_bundle(base_no: str):
            return base_no, self.registry_client.fetch_base_parcel_bundle(base_no)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_base = {executor.submit(fetch_bundle, b): b for b in base_to_features}
            for _completed, fut in enumerate(as_completed(future_to_base), 1):
                base_no, bundle = fut.result()
                if bundle:
                    bundle_cache[base_no] = bundle

        print(f"  -> Retrieved registry bundles for {len(bundle_cache)} / {len(base_to_features)} base parcels.")

        print("Step 3/3: Parsing ownership, reprojecting geometries to WGS84, and assembling GeoJSON...")
        clean_features = []

        for feat in features:
            props = feat.get("properties", {})
            broj = str(props.get("BROJ", "")).strip()
            podbroj = str(props.get("PODBROJ", "0")).strip()
            target_clean = f"{broj}/{podbroj}" if podbroj and podbroj != "0" else broj

            bundle = bundle_cache.get(broj, [])
            matched = self.registry_client.match_sub_parcel(bundle, target_clean) if bundle else None

            owners = []
            parts = []
            date_str = ""

            if matched:
                owners = parse_owners_html(matched.get("posjed_vlasnistvo", ""))
                parts = parse_parts_html(matched.get("dio_parcele", ""))
                date_str = parse_date_html(matched.get("datum_replikacije", ""))

            area = float(props.get("POVRSINA", 0) or 0)
            geom_wgs = self.transformer.transform_geometry(feat["geometry"]) if feat.get("geometry") else None

            clean_features.append(
                {
                    "type": "Feature",
                    "id": str(props.get("PARCELID") or target_clean),
                    "geometry": geom_wgs,
                    "properties": {
                        "parcel_id": target_clean,
                        "broj": broj,
                        "podbroj": podbroj,
                        "pl_broj": str(props.get("PL_BROJ", "")),
                        "ko_naziv": self.city_name,
                        "ko_id": int(self.ko_id),
                        "area_sqm": area,
                        "area_ha": round(area / 10000.0, 4),
                        "n_owners": len(owners),
                        "is_coowned": len(owners) > 1,
                        "owners": owners,
                        "parts": parts,
                        "updated_date": date_str,
                    },
                }
            )

        out_fc = {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
            "metadata": {
                "municipality": self.city_name,
                "ko_id": self.ko_id,
                "total_features": len(clean_features),
            },
            "features": clean_features,
        }

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(out_fc, f, ensure_ascii=False)

        print(f"Pipeline complete! Saved to {out_file}")
        return out_fc
