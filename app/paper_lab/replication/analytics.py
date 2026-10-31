"""Return arithmetic used by replication recipes. Inputs are decimal returns."""

from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
import pandas as pd


def annualize(monthly: pd.Series) -> float:
    r = monthly.dropna()
    if r.empty:
        return float("nan")
    return float(np.prod(1 + r.values) ** (12 / len(r)) - 1)


def calendar_year_returns(monthly: pd.Series, full_years_only: bool = True) -> pd.Series:
    r = monthly.dropna()
    years = r.index.year
    grouped = r.groupby(years)
    out = grouped.apply(lambda x: float(np.prod(1 + x.values) - 1))
    if full_years_only:
        out = out[grouped.size() == 12]
    out.index.name = "year"
    return out


def period_annualized(annual: pd.Series, start: int, end: int, exclude: Iterable[int] = ()) -> float:
    """Geometric annualized return over calendar years [start, end] minus excluded years."""
    excl = set(exclude)
    s = annual[(annual.index >= start) & (annual.index <= end) & (~annual.index.isin(excl))].dropna()
    if s.empty:
        return float("nan")
    return float(np.prod(1 + s.values) ** (1 / len(s)) - 1)


def years_available(annual: pd.Series, start: int, end: int, exclude: Iterable[int] = ()) -> int:
    excl = set(exclude)
    return int(((annual.index >= start) & (annual.index <= end) & (~annual.index.isin(excl))).sum())


def arithmetic_annualized(monthly: pd.Series, start: int, end: int, exclude: Iterable[int] = ()) -> float:
    """Mean monthly return x 12 over calendar years [start, end] (how long-short factors are usually quoted)."""
    excl = set(exclude)
    yrs = monthly.index.year
    s = monthly[(yrs >= start) & (yrs <= end) & (~pd.Index(yrs).isin(excl))].dropna()
    return float(s.mean() * 12) if not s.empty else float("nan")


def rolling_annualized(monthly: pd.Series, window: int = 120) -> pd.Series:
    logr = np.log1p(monthly)
    return np.expm1(logr.rolling(window).sum() * 12 / window)


def rolling_excess(portfolio: pd.Series, benchmark: pd.Series, window: int = 120) -> pd.Series:
    """Trailing-window annualized portfolio return minus annualized benchmark return."""
    df = pd.concat([portfolio, benchmark], axis=1, join="inner").dropna()
    return (rolling_annualized(df.iloc[:, 0], window) - rolling_annualized(df.iloc[:, 1], window)).dropna()


def growth_of_dollar(returns: pd.Series) -> pd.Series:
    return (1 + returns.fillna(0)).cumprod()


def extreme_years(diff: pd.Series, k: int = 4, start: Optional[int] = None, end: Optional[int] = None) -> list[int]:
    s = diff
    if start is not None:
        s = s[s.index >= start]
    if end is not None:
        s = s[s.index <= end]
    return sorted(int(y) for y in s.nlargest(k).index)


def longest_run(mask: Iterable[bool]) -> int:
    best = cur = 0
    for m in mask:
        cur = cur + 1 if m else 0
        best = max(best, cur)
    return best


def bootstrap_underperformance(excess_monthly: pd.Series, horizon_months: int, n_sims: int = 2000,
                               block: int = 12, seed: int = 7) -> np.ndarray:
    """Stationary-ish block bootstrap of monthly excess log-returns.

    Returns the simulated annualized excess for ``n_sims`` paths of ``horizon_months``.
    Preserves the historical mean, volatility and (within-block) autocorrelation, so it
    answers: "if the premium is exactly what history says, how often does an investor
    lose to the market over this horizon by chance alone?"
    """
    x = np.log1p(excess_monthly.dropna().values)
    rng = np.random.default_rng(seed)
    n = len(x)
    n_blocks = int(np.ceil(horizon_months / block))
    starts = rng.integers(0, n - block, size=(n_sims, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n_sims, -1)[:, :horizon_months]
    total = x[idx].sum(axis=1)
    return np.expm1(total * 12 / horizon_months)
