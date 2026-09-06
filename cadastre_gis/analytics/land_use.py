"""
Agronomic and Cadastral Land Use Analysis.
Extracts land capability classes (1st to 8th class), standardizes usage categories,
and computes weighted soil quality indexes.
"""

import re
from typing import Any

import numpy as np
import pandas as pd


def extract_land_class(usage_type: str) -> int | None:
    """
    Extract cadastral land class from usage description.
    Example: 'Њива 3. класе' -> 3
    Example: 'Шума 4. класе' -> 4
    Example: 'Двориште' -> None
    """
    if not usage_type:
        return None
    match = re.search(r"(\d+)\.\s*класе", usage_type, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def categorize_usage(usage_type: str) -> str:
    """
    Categorize granular cadastre land usage into major functional categories:
    - agriculture (njiive, voćnjaci, vinogradi, livade, pašnjaci)
    - residential (stambeni objekat, zgrada, kuća, pomoćni objekat)
    - yard (dvorište)
    - forest (šuma)
    - infrastructure (put, kanal, voda, rijeka, pruga)
    - other (neplodno, ostalo)
    """
    u = (usage_type or "").lower()
    if any(k in u for k in ["стамбен", "зграда", "кућа", "објекат", "помоћни", "кухиња", "шупа", "штала"]):
        return "residential"
    if any(k in u for k in ["двориште", "окућница"]):
        return "yard"
    if any(k in u for k in ["њива", "ораница", "пашњак", "ливада", "воћњак", "виноград", "башта"]):
        return "agriculture"
    if any(k in u for k in ["шума", "забран", "голет"]):
        return "forest"
    if any(k in u for k in ["пут", "канал", "вода", "ријека", "поток", "пјешачка", "насип", "пруга"]):
        return "infrastructure"
    return "other"


def analyze_land_use(df_use: pd.DataFrame, top_n: int = 20) -> dict[str, Any]:
    """
    Calculate area distributions across usage types, land classes, and broad categories.
    """
    if df_use.empty:
        return {}

    total_area = df_use["area_sqm"].sum()

    # By usage type
    by_type = df_use.groupby("usage_type")["area_sqm"].sum().sort_values(ascending=False).head(top_n).round(2).to_dict()

    # By broad category
    df_use["category"] = df_use["usage_type"].apply(categorize_usage)
    by_category = df_use.groupby("category")["area_sqm"].sum().sort_values(ascending=False).round(2).to_dict()
    category_shares = {
        cat: round((area / total_area * 100), 2) if total_area > 0 else 0.0 for cat, area in by_category.items()
    }

    # By land class
    classified = df_use.dropna(subset=["land_class"]).copy()
    if not classified.empty:
        classified["land_class"] = classified["land_class"].astype(int)
        by_class = classified.groupby("land_class")["area_sqm"].sum().sort_index().round(2).to_dict()
        weighted_avg_class = (
            float(np.average(classified["land_class"], weights=classified["area_sqm"]))
            if classified["area_sqm"].sum() > 0
            else None
        )
    else:
        by_class = {}
        weighted_avg_class = None

    return {
        "total_parts_area_sqm": round(total_area, 2),
        "total_parts_area_ha": round(total_area / 10000.0, 4),
        "by_usage_type": by_type,
        "by_category": by_category,
        "category_shares_pct": category_shares,
        "by_class": by_class,
        "weighted_avg_class": round(weighted_avg_class, 3) if weighted_avg_class is not None else None,
    }
