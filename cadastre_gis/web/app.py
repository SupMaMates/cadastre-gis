"""
Flask Web Application and RESTful GIS API.
Provides spatial GeoJSON streaming, parcel queries, analytics endpoints,
and KML export for the web interface.
"""

import csv
import io
import json
from pathlib import Path
from typing import Any

from flask import Flask, Response, abort, jsonify, render_template, request

from cadastre_gis.analytics.engine import CadastreAnalyticsEngine
from cadastre_gis.config import (
    DEFAULT_CITY_NAME,
    DEFAULT_DATASET,
    DEFAULT_KO_ID,
    WEB_DEBUG,
    WEB_HOST,
    WEB_PORT,
)
from cadastre_gis.crs.kml import export_parcel_to_kml


class CadastreDataStore:
    """
    In-memory spatial and attribute data store with indexed search.
    """

    def __init__(self, geojson_path: Path):
        self.geojson_path = Path(geojson_path)
        self.data: dict[str, Any] = {"features": []}
        self.features_by_id: dict[str, dict[str, Any]] = {}
        self.features_by_pl: dict[str, list] = {}
        self.analytics_engine: CadastreAnalyticsEngine | None = None
        self.cached_report: dict[str, Any] | None = None
        self.load_data()

    def load_data(self):
        if not self.geojson_path.exists():
            print(f"Warning: Dataset {self.geojson_path} not found.")
            return

        with open(self.geojson_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self.features_by_id = {}
        self.features_by_pl = {}

        for feat in self.data.get("features", []):
            props = feat.get("properties", {})
            p_id = str(props.get("parcel_id", ""))
            if p_id:
                self.features_by_id[p_id] = feat
                # Also index pure broj
                broj = str(props.get("broj", ""))
                if broj and broj not in self.features_by_id:
                    self.features_by_id[broj] = feat

            pl = str(props.get("pl_broj", ""))
            if pl:
                self.features_by_pl.setdefault(pl, []).append(feat)

        self.analytics_engine = CadastreAnalyticsEngine(self.data)
        self.cached_report = self.analytics_engine.generate_report(top_n=20)
        print(f"Loaded {len(self.features_by_id)} indexed parcel records.")


def create_app(dataset_path: Path | None = None) -> Flask:
    """
    Application factory.
    """
    template_dir = Path(__file__).parent / "templates"
    static_dir = Path(__file__).parent / "static"

    app = Flask(__name__, template_folder=str(template_dir), static_folder=str(static_dir))

    data_path = Path(dataset_path or DEFAULT_DATASET)
    store = CadastreDataStore(data_path)
    app.config["STORE"] = store

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/health")
    def api_health():
        return jsonify(
            {
                "status": "healthy",
                "parcels_count": len(store.data.get("features", [])),
                "dataset": str(store.geojson_path.name),
                "version": "1.0.0",
            }
        )

    @app.route("/api/meta")
    def api_meta():
        meta = store.data.get("metadata", {})
        features = store.data.get("features", [])

        # Calculate bounding box from features
        min_lon, min_lat = 180.0, 90.0
        max_lon, max_lat = -180.0, -90.0

        for f in features[:200]:  # Sample features for quick centroid/bounds
            geom = f.get("geometry")
            if geom and geom.get("coordinates"):
                coords = geom["coordinates"][0] if geom["type"] == "Polygon" else geom["coordinates"][0][0]
                for pt in coords:
                    min_lon = min(min_lon, pt[0])
                    min_lat = min(min_lat, pt[1])
                    max_lon = max(max_lon, pt[0])
                    max_lat = max(max_lat, pt[1])

        bounds = [[min_lat, min_lon], [max_lat, max_lon]] if min_lon < max_lon else [[44.915, 18.617], [44.968, 18.681]]
        center = [(bounds[0][0] + bounds[1][0]) / 2, (bounds[0][1] + bounds[1][1]) / 2]

        return jsonify(
            {
                "municipality": meta.get("municipality", DEFAULT_CITY_NAME),
                "municipality_cir": meta.get("municipality_cir", DEFAULT_CITY_NAME),
                "ko_id": meta.get("ko_id", DEFAULT_KO_ID),
                "total_features": len(features),
                "total_area_sqm": meta.get("total_area_sqm", 0),
                "bounds": bounds,
                "center": center,
                "crs": "EPSG:4326",
            }
        )

    @app.route("/api/parcels")
    def api_parcels():
        search_query = request.args.get("search", "").strip().lower()
        usage_filter = request.args.get("usage", "").strip().lower()
        coowned_only = request.args.get("coowned", "").lower() in ("true", "1")
        anomalies_only = request.args.get("anomalies", "").lower() in ("true", "1")
        min_area = request.args.get("min_area", type=float)
        max_area = request.args.get("max_area", type=float)
        limit = request.args.get("limit", type=int)

        all_features = store.data.get("features", [])

        # Apply filters if requested
        if not (search_query or usage_filter or coowned_only or anomalies_only or min_area or max_area or limit):
            # Return full dataset directly
            return jsonify(store.data)

        filtered = []
        for feat in all_features:
            props = feat.get("properties", {})

            # Search filter (matches parcel_id, PL number, or owner names)
            if search_query:
                p_id = str(props.get("parcel_id", "")).lower()
                pl = str(props.get("pl_broj", "")).lower()
                names = str(props.get("owner_names", "")).lower()
                if not (search_query in p_id or search_query in pl or search_query in names):
                    continue

            # Usage category filter
            if usage_filter and usage_filter != "all" and props.get("usage_category", "").lower() != usage_filter:
                continue

            # Co-ownership filter
            if coowned_only and not props.get("is_coowned"):
                continue

            # Anomalies filter
            if anomalies_only and not props.get("has_share_anomaly"):
                continue

            # Area range
            area = float(props.get("area_sqm", 0))
            if min_area is not None and area < min_area:
                continue
            if max_area is not None and area > max_area:
                continue

            filtered.append(feat)
            if limit and len(filtered) >= limit:
                break

        return jsonify({"type": "FeatureCollection", "crs": store.data.get("crs"), "features": filtered})

    @app.route("/api/parcels/<path:parcel_id>")
    def api_parcel_detail(parcel_id):
        # Decode slash if present (e.g. 1376/2)
        clean_id = parcel_id.strip()
        feat = store.features_by_id.get(clean_id)

        if not feat:
            # Try matching with or without sub-number
            clean_id_alt = clean_id.replace("-", "/")
            feat = store.features_by_id.get(clean_id_alt)

        if not feat:
            abort(404, description=f"Parcel {parcel_id} not found.")

        return jsonify(feat)

    @app.route("/api/parcels/<path:parcel_id>/kml")
    def api_parcel_kml(parcel_id):
        clean_id = parcel_id.strip()
        feat = store.features_by_id.get(clean_id) or store.features_by_id.get(clean_id.replace("-", "/"))
        if not feat:
            abort(404, description=f"Parcel {parcel_id} not found.")

        kml_content = export_parcel_to_kml(feat)
        filename = f"parcel_{clean_id.replace('/', '_')}.kml"

        return Response(
            kml_content,
            mimetype="application/vnd.google-earth.kml+xml",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    @app.route("/api/analytics")
    def api_analytics():
        top_n = request.args.get("top_n", 20, type=int)
        include_entities = request.args.get("include_entities", "true").lower() in ("true", "1")

        if store.cached_report and top_n == 20 and include_entities:
            return jsonify(store.cached_report)

        if store.analytics_engine:
            report = store.analytics_engine.generate_report(top_n=top_n, include_entities=include_entities)
            return jsonify(report)

        abort(500, description="Analytics engine not initialized.")

    @app.route("/api/export")
    def api_export():
        fmt = request.args.get("format", "geojson").lower()
        search = request.args.get("search", "").strip().lower()

        features = store.data.get("features", [])
        if search:
            features = [
                f
                for f in features
                if search in str(f.get("properties", {}).get("parcel_id", "")).lower()
                or search in str(f.get("properties", {}).get("owner_names", "")).lower()
            ]

        if fmt == "csv":
            si = io.StringIO()
            writer = csv.writer(si)
            writer.writerow(
                ["parcel_id", "pl_broj", "area_sqm", "n_owners", "primary_owner", "primary_usage", "is_coowned"]
            )
            for f in features:
                p = f.get("properties", {})
                writer.writerow(
                    [
                        p.get("parcel_id"),
                        p.get("pl_broj"),
                        p.get("area_sqm"),
                        p.get("n_owners"),
                        p.get("primary_owner"),
                        p.get("primary_usage"),
                        p.get("is_coowned"),
                    ]
                )
            return Response(
                si.getvalue(),
                mimetype="text/csv",
                headers={"Content-Disposition": "attachment; filename=parcels_export.csv"},
            )

        # Default GeoJSON
        fc = {"type": "FeatureCollection", "crs": store.data.get("crs"), "features": features}
        return Response(
            json.dumps(fc, ensure_ascii=False),
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=parcels_export.geojson"},
        )

    return app


def main():
    app = create_app()
    print(f"Starting CadastreGIS server at http://{WEB_HOST}:{WEB_PORT}")
    app.run(host=WEB_HOST, port=WEB_PORT, debug=WEB_DEBUG)


if __name__ == "__main__":
    main()
