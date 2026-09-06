"""
Comprehensive Cadastre Analytics Engine.
Orchestrates econometric, demographic, spatial, and fragmentation analyses,
producing structured JSON reports, exportable CSVs, and Rich terminal summaries.
"""

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from cadastre_gis.analytics.demographics import analyze_clans, analyze_demographics, parse_balkan_name
from cadastre_gis.analytics.fragmentation import (
    analyze_parcel_fragmentation,
    detect_micro_shares,
    detect_share_anomalies,
)
from cadastre_gis.analytics.inequality import gini, hhi, lorenz_curve, palma_ratio, theil, top_share
from cadastre_gis.analytics.land_use import analyze_land_use, extract_land_class


class CadastreAnalyticsEngine:
    """
    Main analytical engine for cadastral dataset processing.
    """

    def __init__(self, geojson_source: str | Path | dict[str, Any]):
        if isinstance(geojson_source, (str, Path)):
            with open(geojson_source, "r", encoding="utf-8") as f:
                self.geojson_data = json.load(f)
        else:
            self.geojson_data = geojson_source

        self.df_parcels, self.df_owners, self.df_parts = self._extract_dataframes()

    def _extract_dataframes(self):
        parcel_rows = []
        owner_rows = []
        part_rows = []

        features = self.geojson_data.get("features", [])

        for feat in features:
            props = feat.get("properties", {}) or {}

            parcel_id = str(props.get("parcel_id") or props.get("BROJ") or "")
            area_sqm = float(props.get("area_sqm") or props.get("POVRSINA") or 0.0)
            broj = str(props.get("broj") or props.get("BROJ") or "")
            podbroj = str(props.get("podbroj") or props.get("PODBROJ") or "0")
            pl_broj = str(props.get("pl_broj") or props.get("PL_BROJ") or "")

            parcel_rows.append(
                {
                    "parcel_id": parcel_id,
                    "broj": broj,
                    "podbroj": podbroj,
                    "pl_broj": pl_broj,
                    "parcel_area_sqm": area_sqm,
                }
            )

            # Extract owners
            owners = props.get("owners") or props.get("REGISTRY_OWNERS") or []
            for o in owners:
                name = str(o.get("name") or o.get("ime") or "").strip()
                share_float = float(o.get("share") or o.get("share_float") or 0.0)
                if not share_float and "share_raw" in o:
                    share_float = float(o.get("share_float", 1.0))

                sur = o.get("surname")
                fath = o.get("father")
                first = o.get("first_name")
                gend = o.get("gender")

                if not sur or not gend:
                    sur, fath, first, gend = parse_balkan_name(name)

                wealth_sqm = float(o.get("wealth_sqm") or (area_sqm * share_float))

                owner_rows.append(
                    {
                        "parcel_id": parcel_id,
                        "name": name,
                        "surname": sur,
                        "father": fath,
                        "first_name": first,
                        "gender": gend,
                        "share": share_float,
                        "share_raw": str(o.get("share_raw") or o.get("udio") or "1/1"),
                        "wealth_sqm": wealth_sqm,
                        "parcel_area_sqm": area_sqm,
                    }
                )

            # Extract land use parts
            parts = props.get("parts") or props.get("REGISTRY_PARTS") or []
            for pt in parts:
                ut = str(pt.get("usage_type") or pt.get("nacin_koriscenja") or "Nepoznato").strip()
                pt_area = float(pt.get("area_sqm") or 0.0)
                lc = pt.get("land_class") or extract_land_class(ut)

                part_rows.append({"parcel_id": parcel_id, "usage_type": ut, "area_sqm": pt_area, "land_class": lc})

        df_parcels = pd.DataFrame(parcel_rows)
        df_owners = pd.DataFrame(owner_rows)
        df_parts = pd.DataFrame(part_rows)

        return df_parcels, df_owners, df_parts

    def generate_report(self, top_n: int = 20, include_entities: bool = True) -> dict[str, Any]:
        """
        Generate comprehensive cadastre analytics report.
        """
        df_parcels = self.df_parcels
        df_owners = self.df_owners
        df_parts = self.df_parts

        total_parcel_area = float(df_parcels["parcel_area_sqm"].sum()) if not df_parcels.empty else 0.0

        # Fragmentation analysis
        df_fragmentation = analyze_parcel_fragmentation(df_parcels, df_owners)

        # Private ownership subset
        if include_entities:
            df_active_owners = df_owners.copy()
        else:
            df_active_owners = df_owners[df_owners["gender"] != "Entity"].copy()

        # Aggregated owner wealth
        owner_wealth = df_active_owners.groupby("name")["wealth_sqm"].sum().sort_values(ascending=False)
        total_active_area = float(owner_wealth.sum())
        wealth_values = owner_wealth.values

        # Core inequality metrics
        metrics = {
            "total_parcels": int(df_parcels["parcel_id"].nunique()),
            "total_owner_records": len(df_owners),
            "unique_owners_count": int(df_active_owners["name"].nunique()),
            "total_cadastre_area_sqm": round(total_parcel_area, 2),
            "total_cadastre_area_ha": round(total_parcel_area / 10000.0, 4),
            "total_analyzed_land_sqm": round(total_active_area, 2),
            "total_analyzed_land_ha": round(total_active_area / 10000.0, 4),
            "gini_coefficient": round(gini(wealth_values), 4),
            "theil_index": round(theil(wealth_values), 4),
            "hhi_index": round(hhi(wealth_values), 6),
            "palma_ratio": round(palma_ratio(owner_wealth), 3),
            "top_1pct_share": round(top_share(owner_wealth, 0.01) * 100, 2),
            "top_5pct_share": round(top_share(owner_wealth, 0.05) * 100, 2),
            "top_10pct_share": round(top_share(owner_wealth, 0.10) * 100, 2),
            "top_20pct_share": round(top_share(owner_wealth, 0.20) * 100, 2),
        }

        # Wealth statistics
        wealth_stats = {}
        if len(wealth_values) > 0:
            wealth_stats = {
                "mean_sqm": round(float(np.mean(wealth_values)), 2),
                "median_sqm": round(float(np.median(wealth_values)), 2),
                "min_sqm": round(float(np.min(wealth_values)), 2),
                "max_sqm": round(float(np.max(wealth_values)), 2),
                "std_sqm": round(float(np.std(wealth_values)), 2),
                "p75_sqm": round(float(np.percentile(wealth_values, 75)), 2),
                "p90_sqm": round(float(np.percentile(wealth_values, 90)), 2),
                "p95_sqm": round(float(np.percentile(wealth_values, 95)), 2),
                "p99_sqm": round(float(np.percentile(wealth_values, 99)), 2),
            }

        # Top landowners
        top_owners = owner_wealth.head(top_n).round(2).to_dict()

        # Micro-owners
        bottom_positive = owner_wealth[owner_wealth > 0].sort_values(ascending=True).head(top_n).round(2).to_dict()

        # Clan & lineage analytics
        clan_analytics = analyze_clans(df_owners, top_n=top_n)

        # Demographics & Gender
        demographics = analyze_demographics(df_owners)

        # Land use
        land_use_analytics = analyze_land_use(df_parts, top_n=top_n)

        # Fragmentation breakdown
        coowned_parcels = df_fragmentation[df_fragmentation["is_coowned"]]
        fragmentation_summary = {
            "total_coowned_parcels": len(coowned_parcels),
            "coowned_parcels_pct": round((len(coowned_parcels) / len(df_fragmentation) * 100), 2)
            if len(df_fragmentation)
            else 0.0,
            "max_owners_on_single_parcel": int(df_fragmentation["n_owners"].max()) if not df_fragmentation.empty else 0,
            "mean_owners_per_parcel": round(float(df_fragmentation["n_owners"].mean()), 2)
            if not df_fragmentation.empty
            else 0.0,
        }

        # Most fragmented parcels
        most_fragmented = (
            df_fragmentation.sort_values(["n_owners", "effective_n_owners"], ascending=False)
            .head(top_n)[["parcel_id", "parcel_area_sqm", "n_owners", "effective_n_owners", "share_sum"]]
            .to_dict(orient="records")
        )

        # Anomalies
        anomalies = detect_share_anomalies(df_owners, tolerance=0.01).head(top_n).to_dict(orient="records")

        # Micro shares
        micro_shares = (
            detect_micro_shares(df_owners, threshold=0.02)
            .head(top_n)[["name", "parcel_id", "share_raw", "share", "wealth_sqm"]]
            .to_dict(orient="records")
        )

        # Lorenz curve
        lorenz_pts = lorenz_curve(wealth_values, n_points=50)

        return {
            "metadata": {
                "municipality": "Donji Žabar",
                "ko_id": 57062,
                "include_entities": include_entities,
                "top_n": top_n,
            },
            "metrics": metrics,
            "wealth_distribution": wealth_stats,
            "top_owners": top_owners,
            "micro_owners": bottom_positive,
            "clans": clan_analytics,
            "demographics": demographics,
            "land_use": land_use_analytics,
            "fragmentation": fragmentation_summary,
            "most_fragmented_parcels": most_fragmented,
            "share_anomalies": anomalies,
            "micro_shares": micro_shares,
            "lorenz_curve": lorenz_pts,
        }

    def export_csvs(self, export_dir: str | Path):
        """
        Export normalized tables to CSV files.
        """
        export_dir = Path(export_dir)
        export_dir.mkdir(parents=True, exist_ok=True)

        self.df_parcels.to_csv(export_dir / "parcels.csv", index=False, encoding="utf-8")
        self.df_owners.to_csv(export_dir / "owners.csv", index=False, encoding="utf-8")
        self.df_parts.to_csv(export_dir / "land_use_parts.csv", index=False, encoding="utf-8")

        # Parcel fragmentation table
        df_frag = analyze_parcel_fragmentation(self.df_parcels, self.df_owners)
        df_frag.to_csv(export_dir / "parcels_fragmentation.csv", index=False, encoding="utf-8")

        # Owner profile summary
        owner_summary = (
            self.df_owners.groupby("name")
            .agg(
                total_wealth_sqm=("wealth_sqm", "sum"),
                parcels_count=("parcel_id", "nunique"),
                gender=("gender", "first"),
                surname=("surname", "first"),
            )
            .sort_values("total_wealth_sqm", ascending=False)
            .reset_index()
        )
        owner_summary.to_csv(export_dir / "owners_summary.csv", index=False, encoding="utf-8")
