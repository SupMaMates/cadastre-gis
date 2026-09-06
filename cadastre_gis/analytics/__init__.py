"""
Cadastre Econometrics, Inequality, Demographics, and Land Fragmentation Analysis.
"""

from cadastre_gis.analytics.demographics import (
    analyze_clans,
    analyze_demographics,
    is_entity_name,
    parse_balkan_name,
    shannon_entropy,
)
from cadastre_gis.analytics.engine import CadastreAnalyticsEngine
from cadastre_gis.analytics.fragmentation import (
    analyze_parcel_fragmentation,
    detect_micro_shares,
    detect_share_anomalies,
    effective_owners,
)
from cadastre_gis.analytics.inequality import (
    gini,
    hhi,
    lorenz_curve,
    palma_ratio,
    theil,
    top_share,
)
from cadastre_gis.analytics.land_use import (
    analyze_land_use,
    categorize_usage,
    extract_land_class,
)

__all__ = [
    "CadastreAnalyticsEngine",
    "analyze_clans",
    "analyze_demographics",
    "analyze_land_use",
    "analyze_parcel_fragmentation",
    "categorize_usage",
    "detect_micro_shares",
    "detect_share_anomalies",
    "effective_owners",
    "extract_land_class",
    "gini",
    "hhi",
    "is_entity_name",
    "lorenz_curve",
    "palma_ratio",
    "parse_balkan_name",
    "shannon_entropy",
    "theil",
    "top_share",
]
