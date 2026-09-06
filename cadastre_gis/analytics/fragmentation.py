"""
Cadastral Land Fragmentation and Inheritance Diagnostics.

Identifies co-ownership clusters, fractional inheritance gridlock ("inheritance nightmares"),
effective number of owners per parcel, and cadastre data quality anomalies.
"""

import numpy as np
import pandas as pd


def effective_owners(shares: np.ndarray | list[float] | pd.Series) -> float:
    """
    Calculate the effective number of owners (inverse Herfindahl index):
    N_eff = 1 / sum(s_i^2)
    where s_i is the fractional share of owner i normalized so sum(s_i) = 1.
    If 1 owner with 100% share -> N_eff = 1.0.
    If 2 owners with 50% each -> N_eff = 2.0.
    If 1 owner has 99% and 10 owners have 0.1% -> N_eff ≈ 1.02.
    """
    s = np.asarray(shares, dtype=float)
    s = s[np.isfinite(s)]
    s = s[s > 0]
    if s.size == 0:
        return 0.0
    total = s.sum()
    if np.isclose(total, 0.0):
        return 0.0
    p = s / total
    denom = np.sum(p * p)
    return float(1.0 / denom) if denom > 0 else 0.0


def analyze_parcel_fragmentation(df_parcels: pd.DataFrame, df_owners: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate owner records by parcel to evaluate co-ownership and fragmentation metrics.
    """
    if df_owners.empty or df_parcels.empty:
        return df_parcels.copy()

    grouped = df_owners.groupby("parcel_id")

    n_owners = grouped["name"].nunique().rename("n_owners")
    share_sum = grouped["share"].sum().rename("share_sum")
    min_share = grouped["share"].min().rename("min_share")
    max_share = grouped["share"].max().rename("max_share")
    eff_owners = grouped["share"].apply(effective_owners).rename("effective_n_owners")

    stats = pd.concat([n_owners, share_sum, min_share, max_share, eff_owners], axis=1)

    result = df_parcels.set_index("parcel_id").join(stats, how="left").reset_index()
    result["n_owners"] = result["n_owners"].fillna(0).astype(int)
    result["effective_n_owners"] = result["effective_n_owners"].fillna(0.0).round(2)
    result["share_sum"] = result["share_sum"].fillna(0.0).round(4)
    result["share_sum_delta"] = (result["share_sum"] - 1.0).abs().round(4)
    result["is_coowned"] = result["n_owners"] > 1

    return result


def detect_micro_shares(df_owners: pd.DataFrame, threshold: float = 0.05) -> pd.DataFrame:
    """
    Identify micro-shares (e.g. share < 5% or 1/20) which typify multigenerational inheritance division.
    """
    if df_owners.empty:
        return pd.DataFrame()

    micro = df_owners[
        (df_owners["gender"] != "Entity") & (df_owners["share"] > 0) & (df_owners["share"] <= threshold)
    ].copy()

    return micro.sort_values(["share", "wealth_sqm"], ascending=[True, True])


def detect_share_anomalies(df_owners: pd.DataFrame, tolerance: float = 0.01) -> pd.DataFrame:
    """
    Detect parcels where the sum of ownership shares deviates from 1.0 by more than tolerance.
    Flags registry discrepancies, disputed titles, or unrecorded inheritances.
    """
    if df_owners.empty:
        return pd.DataFrame()

    share_sums = (
        df_owners.groupby("parcel_id")
        .agg(
            share_sum=("share", "sum"),
            n_owners=("name", "count"),
            parcel_area_sqm=("wealth_sqm", lambda x: df_owners.loc[x.index, "wealth_sqm"].sum() if len(x) else 0),
        )
        .reset_index()
    )

    share_sums["deviation"] = (share_sums["share_sum"] - 1.0).abs()
    anomalies = share_sums[share_sums["deviation"] > tolerance].sort_values("deviation", ascending=False)
    return anomalies
