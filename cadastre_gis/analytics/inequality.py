"""
Inequality and Concentration Metrics for Cadastral Landholdings.
Implements Gini coefficient, Theil index, Herfindahl-Hirschman Index (HHI),
Palma ratio, Lorenz curve, and top-percentile land wealth shares.
"""

import numpy as np
import pandas as pd


def gini(values: np.ndarray | list[float] | pd.Series) -> float:
    """
    Compute Gini coefficient of inequality [0, 1].
    0 = absolute equality, 1 = complete inequality (one person owns all land).
    """
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    x = x[x >= 0]
    if x.size == 0 or np.isclose(x.sum(), 0.0):
        return 0.0

    x = np.sort(x)
    n = x.size
    idx = np.arange(1, n + 1)
    return float(np.sum((2 * idx - n - 1) * x) / (n * np.sum(x)))


def theil(values: np.ndarray | list[float] | pd.Series) -> float:
    """
    Compute Theil entropy index of inequality.
    """
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    x = x[x > 0]
    if x.size == 0:
        return 0.0
    mu = x.mean()
    if np.isclose(mu, 0.0):
        return 0.0
    return float(np.mean((x / mu) * np.log(x / mu)))


def hhi(shares_or_values: np.ndarray | list[float] | pd.Series) -> float:
    """
    Herfindahl-Hirschman Index (HHI) for land concentration.
    Returns normalized value in [0, 1].
    """
    s = np.asarray(shares_or_values, dtype=float)
    s = s[np.isfinite(s)]
    s = s[s >= 0]
    total = s.sum()
    if np.isclose(total, 0.0):
        return 0.0
    p = s / total
    return float(np.sum(p * p))


def top_share(series: pd.Series | np.ndarray | list[float], pct: float) -> float:
    """
    Share of total land area owned by top pct fraction of owners (e.g. 0.01 for top 1%).
    """
    if isinstance(series, (np.ndarray, list)):
        series = pd.Series(series)
    series = series.dropna()
    series = series[series > 0]
    total = series.sum()
    if len(series) == 0 or np.isclose(total, 0.0):
        return 0.0

    n = len(series)
    k = max(1, round(n * pct))
    top_sum = series.sort_values(ascending=False).head(k).sum()
    return float(top_sum / total)


def palma_ratio(series: pd.Series | np.ndarray | list[float]) -> float:
    """
    Palma ratio: share of total land owned by the top 10% divided by share of bottom 40%.
    """
    if isinstance(series, (np.ndarray, list)):
        series = pd.Series(series)
    series = series.dropna()
    series = series[series > 0]
    total = series.sum()
    if len(series) == 0 or np.isclose(total, 0.0):
        return 0.0

    n = len(series)
    top_k = max(1, round(n * 0.10))
    bot_k = max(1, round(n * 0.40))

    s_sorted = series.sort_values(ascending=True)
    bottom_share = s_sorted.head(bot_k).sum()
    top_share_val = s_sorted.tail(top_k).sum()

    if np.isclose(bottom_share, 0.0):
        return float("inf")
    return float(top_share_val / bottom_share)


def lorenz_curve(values: np.ndarray | list[float] | pd.Series, n_points: int = 50) -> list[dict[str, float]]:
    """
    Compute Lorenz curve coordinates (population_share, wealth_share) for visualization.
    Returns list of dicts: [{'p': 0.0, 'l': 0.0, 'equality': 0.0}, ...]
    """
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    x = x[x >= 0]
    if x.size == 0 or np.isclose(x.sum(), 0.0):
        return [
            {"p": round(float(p), 3), "l": round(float(p), 3), "equality": round(float(p), 3)}
            for p in np.linspace(0, 1, n_points)
        ]

    x = np.sort(x)
    total_wealth = x.sum()
    n = len(x)

    cum_wealth = np.concatenate(([0.0], np.cumsum(x) / total_wealth))
    cum_pop = np.concatenate(([0.0], np.arange(1, n + 1) / n))

    # Sample evenly spaced points along [0, 1]
    target_p = np.linspace(0, 1, n_points)
    interpolated_l = np.interp(target_p, cum_pop, cum_wealth)

    points = []
    for p, l in zip(target_p, interpolated_l):
        points.append(
            {"p": round(float(p) * 100, 2), "l": round(float(l) * 100, 2), "equality": round(float(p) * 100, 2)}
        )
    return points
