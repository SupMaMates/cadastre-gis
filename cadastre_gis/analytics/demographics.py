"""
Demographics, Balkan Name Parsing, and Clan Lineage Analytics.
Handles patronymics (father's name), gender heuristics, legal entity classification,
and Shannon entropy of name diversity across cadastral records.
"""

import re
from typing import Any

import numpy as np
import pandas as pd

ENTITY_KEYWORDS = [
    "РЕПУБЛИКА",
    "OPŠTINA",
    "ОПШТИНА",
    "REPUBLIKA",
    "GRAD",
    "ГРАД",
    "ЈП",
    "JP",
    "D.O.O",
    "Д.О.О",
    "AD",
    "A.D",
    "АКЦИОНАРСКО",
    "FOND",
    "FONDACIJA",
    "MINISTARSTVO",
    "МИНИСТАРСТВО",
    "MINISTAR",
    "CRKVA",
    "ЦРКВА",
    "MANASTIR",
    "МАНАСТИР",
    "SAVEZ",
    "DRUŠTVO",
    "ДРУШТВО",
    "KOMPANIJA",
    "BANKA",
    "БАНКА",
    "VODOVOD",
    "ŠUME",
]


def normalize_spaces(s: str) -> str:
    """Normalize consecutive whitespace characters and trim edges."""
    return re.sub(r"\s+", " ", (s or "").strip())


def is_entity_name(name: str) -> bool:
    """Check if a name string represents an institutional/legal entity or church/state."""
    up = (name or "").upper()
    return any(k in up for k in ENTITY_KEYWORDS)


def parse_balkan_name(full_name: str) -> tuple[str, str, str, str]:
    """
    Parse standard Balkan cadastral name notation:
    Format: 'SURNAME (FATHER) FIRSTNAME'
    Example: 'Мутавчић (Живана) Ратко' -> ('Мутавчић', 'Живана', 'Ратко', 'Male')
    Example: 'Ђокановић (Славка) Младен' -> ('Ђокановић', 'Славка', 'Младен', 'Male')
    Example: 'ОПШТИНА ДОЊИ ЖАБАР' -> ('ОПШТИНА ДОЊИ ЖАБАР', 'Unknown', 'Unknown', 'Entity')

    Returns:
        (surname, father, first_name, gender)
    """
    name_clean = normalize_spaces(full_name)
    if not name_clean:
        return ("Unknown", "Unknown", "Unknown", "Unknown")

    if is_entity_name(name_clean):
        return (name_clean, "Unknown", "Unknown", "Entity")

    # Match: Surname (Father) Firstname
    match = re.search(r"^(.*?)\s*\((.*?)\)\s*(.*)$", name_clean)
    if match:
        surname = normalize_spaces(match.group(1))
        father = normalize_spaces(match.group(2))
        first_name = normalize_spaces(match.group(3))
    else:
        # Fallback split
        parts = name_clean.split(" ")
        if len(parts) >= 2:
            surname = parts[0]
            father = "Unknown"
            first_name = " ".join(parts[1:])
        else:
            surname = name_clean
            father = "Unknown"
            first_name = "Unknown"

    # Gender heuristic for Slavic/Balkan first names
    # Predominant rule: Feminine given names typically end in 'a' (Latin 'a' or Cyrillic 'а')
    # Masculine names ending in 'a' (e.g. Nikola, Luka, Ilija) are handled as exceptions.
    fn_lower = first_name.lower()
    male_exceptions = {
        "nikola",
        "luka",
        "kosta",
        "ilija",
        "nemanja",
        "matija",
        "andrija",
        "sava",
        "pera",
        "bora",
        "никола",
        "лука",
        "коста",
        "илија",
        "немања",
        "матија",
        "андрија",
        "сава",
        "пера",
        "бора",
    }
    if fn_lower.endswith(("a", "а")) and fn_lower not in male_exceptions:
        gender = "Female"
    else:
        gender = "Male"

    return (surname, father, first_name, gender)


def shannon_entropy(series: pd.Series | list[int] | np.ndarray) -> float:
    """
    Calculate Shannon information entropy of frequency counts.
    Higher entropy indicates greater diversity / dispersion of names.
    """
    if isinstance(series, (list, np.ndarray)):
        series = pd.Series(series)
    counts = series.dropna()
    total = counts.sum()
    if len(counts) == 0 or np.isclose(total, 0.0):
        return 0.0
    p = (counts / total).values.astype(float)
    p = p[p > 0]
    return float(-np.sum(p * np.log(p)))


def analyze_clans(df_owners: pd.DataFrame, top_n: int = 20) -> dict[str, Any]:
    """
    Analyze clan and lineage concentration by surname and household cluster (surname | father).
    """
    if df_owners.empty:
        return {}

    private_owners = df_owners[df_owners["gender"] != "Entity"].copy()
    if private_owners.empty:
        return {}

    # Unique individuals
    unique_persons = private_owners.drop_duplicates("name").copy()

    # Surname frequencies
    surname_freq = unique_persons["surname"].value_counts().head(top_n).to_dict()

    # Surname wealth
    surname_wealth = (
        private_owners.groupby("surname")["wealth_sqm"]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
        .round(2)
        .to_dict()
    )

    # Lineage / household key (surname + father)
    private_owners["family_key"] = (
        private_owners["surname"].fillna("Unknown") + " (" + private_owners["father"].fillna("Unknown") + ")"
    )
    family_wealth = (
        private_owners.groupby("family_key")["wealth_sqm"]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
        .round(2)
        .to_dict()
    )

    # Shannon diversity entropies
    all_surnames = unique_persons["surname"].value_counts()
    all_first_names = unique_persons[unique_persons["first_name"] != "Unknown"]["first_name"].value_counts()
    all_fathers = unique_persons[unique_persons["father"] != "Unknown"]["father"].value_counts()

    return {
        "surname_frequency": surname_freq,
        "surname_wealth": surname_wealth,
        "family_wealth": family_wealth,
        "entropy_surname": round(shannon_entropy(all_surnames), 4),
        "entropy_first_name": round(shannon_entropy(all_first_names), 4),
        "entropy_father": round(shannon_entropy(all_fathers), 4),
        "unique_surnames_count": len(all_surnames),
        "unique_first_names_count": len(all_first_names),
    }


def analyze_demographics(df_owners: pd.DataFrame) -> dict[str, Any]:
    """
    Aggregate demographic gender splits and institutional ownership.
    """
    if df_owners.empty:
        return {}

    unique_persons = df_owners.drop_duplicates("name").copy()
    counts_by_gender = unique_persons["gender"].value_counts().to_dict()

    wealth_by_gender = df_owners.groupby("gender")["wealth_sqm"].sum().round(2).to_dict()
    total_wealth = sum(wealth_by_gender.values())

    wealth_shares = {
        g: round((w / total_wealth * 100), 2) if total_wealth > 0 else 0.0 for g, w in wealth_by_gender.items()
    }

    private_owners = df_owners[df_owners["gender"] != "Entity"]
    median_by_gender = (
        private_owners.groupby("gender")
        .apply(lambda sub: sub.groupby("name")["wealth_sqm"].sum().median())
        .round(2)
        .to_dict()
    )
    mean_by_gender = (
        private_owners.groupby("gender")
        .apply(lambda sub: sub.groupby("name")["wealth_sqm"].sum().mean())
        .round(2)
        .to_dict()
    )

    return {
        "counts": counts_by_gender,
        "wealth_sqm": wealth_by_gender,
        "wealth_share_pct": wealth_shares,
        "median_wealth_sqm": median_by_gender,
        "mean_wealth_sqm": mean_by_gender,
    }
