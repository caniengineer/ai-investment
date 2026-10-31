"""Recipe: long-only size/value factor fluctuation vs the market.

Built for McQuarrie (2025) "Do Factor Strategies Beat the Market? Sometimes Yes.
Sometimes No." (SSRN 5098799) but driven by the paper's ``PaperInsights`` so it works
for any paper making sub-period small-vs-market / rolling factor-vs-market claims.

Public-data proxies (the paper's SBBI and DFA series are proprietary / spliced):
  small stocks  -> French Portfolios_Formed_on_ME, value-weighted 'Lo 20' (configurable)
  S&P / market  -> French Mkt-RF + RF
  SMB           -> French SMB, mean monthly x 12
  anti-factor   -> French 6_Portfolios_2x3 'BIG LoBM'
  large value   -> French 6_Portfolios_2x3 'BIG HiBM'

Proxy data will not match levels to the basis point; the checks therefore grade
*pattern* fidelity (signs, magnitudes within a band, timing of extremes) and say so.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from app.paper_lab.replication import ReplicationResult, compare_to_result, compare_value
from app.paper_lab.replication import analytics as A
from app.paper_lab.replication import french
from app.paper_lab.schema import CheckResult, NumericResult, PaperInsights

logger = logging.getLogger("alphaagent.paper_lab.recipe.factor_fluctuation")

DESCRIPTION = ("Size/value long-only vs market: sub-period table, extreme-year probes, trailing "
               "120m anti-factor and large-value spreads, bootstrap test of 'random fluctuation' "
               "(Ken French data; optional fund data via yfinance).")

DEFAULT_PERIODS = [
    ("all", 1926, 2023), ("three_period", 1926, 1963), ("three_period", 1964, 1981), ("three_period", 1982, 2023),
    ("six_period", 1926, 1941), ("six_period", 1942, 1963), ("six_period", 1964, 1981),
    ("six_period", 1982, 1999), ("six_period", 2000, 2017), ("six_period", 2018, 2023),
]


def _find(ins: Optional[PaperInsights], keyword: str, start: int, end: int, group: Optional[str],
          excluded: tuple = ()) -> Optional[NumericResult]:
    if ins is None:
        return None
    for r in ins.numeric_results:
        if (keyword in r.series.lower() and r.period_start == start and r.period_end == end
                and r.metric.startswith("annualized_return") and tuple(sorted(r.excluded_years)) == tuple(sorted(excluded))
                and (group is None or r.group == group)):
            return r
    return None


def _small(ins, s, e, g, ex=()):
    return _find(ins, "small", s, e, g, ex)


def _mkt(ins, s, e, g, ex=()):
    return _find(ins, "s&p", s, e, g, ex) or _find(ins, "market", s, e, g, ex)


def _smb(ins, s, e, g, ex=()):
    return _find(ins, "smb", s, e, g, ex)


def _periods(ins: Optional[PaperInsights]) -> list[tuple[str, int, int]]:
    if ins is None:
        return DEFAULT_PERIODS
    seen, out = set(), []
    for r in ins.numeric_results:
        if ("small" in r.series.lower() and r.metric == "annualized_return" and r.period_start
                and r.period_end and not r.excluded_years):
            key = (r.group or "", r.period_start, r.period_end)
            if key not in seen:
                seen.add(key)
                out.append(key)
    return out or DEFAULT_PERIODS


def _excluded_sets(ins: Optional[PaperInsights]) -> list[tuple[str, tuple[int, ...]]]:
    if ins is None:
        return [("skew_drop_extreme", (1933, 1943, 1945, 1967)), ("skew_drop_ww2", (1942, 1943, 1944, 1945))]
    seen, out = set(), []
    for r in ins.numeric_results:
        if "small" in r.series.lower() and r.excluded_years:
            key = tuple(sorted(r.excluded_years))
            if key not in seen:
                seen.add(key)
                out.append((r.group or "excluded", key))
    return out


def load_data(data_dir=None, cache_dir=None, offline=False, small_column="Lo 20") -> dict[str, pd.Series]:
    kw = dict(data_dir=data_dir, cache_dir=cache_dir, offline=offline)
    f = french.market_and_factors(**kw)
    me = french.size_portfolios(**kw)
    six = french.size_bm_2x3(**kw)
    return {
        "MKT": f["MKT"], "SMB": f["SMB"], "HML": f["HML"], "RF": f["RF"],
        "SMALL": me[small_column], "BIG_LoBM": six["BIG LoBM"], "BIG_HiBM": six["BIG HiBM"],
    }


def run(insights: Optional[PaperInsights] = None, data: Optional[dict[str, pd.Series]] = None,
        data_dir=None, cache_dir=None, offline: bool = False, small_column: str = "Lo 20",
        window: int = 120, with_funds: bool = False, n_sims: int = 2000) -> ReplicationResult:
    res = ReplicationResult(recipe="factor-fluctuation")
    if data is None:
        data = load_data(data_dir, cache_dir, offline, small_column)
    res.notes.append(f"Small-stock proxy: French ME portfolio '{small_column}' (value-weighted); "
                     "market proxy: French Mkt-RF + RF. The paper uses SBBI (to 1981) spliced with "
                     "DFA Microcap / Vanguard 500 funds, so levels will differ; signs and timing should not.")

    small_a = A.calendar_year_returns(data["SMALL"])
    mkt_a = A.calendar_year_returns(data["MKT"])
    diff_a = (small_a - mkt_a).dropna()
    first_year = int(small_a.index.min())
    if first_year > 1926:
        res.notes.append(f"French data has full calendar years from {first_year}; earlier years are dropped.")

    # ---- Exhibit 3: sub-period table ---------------------------------------
    rows = []
    for g, s, e in _periods(insights):
        sm = A.period_annualized(small_a, s, e) * 100
        mk = A.period_annualized(mkt_a, s, e) * 100
        smb = A.arithmetic_annualized(data["SMB"], s, e) * 10_000
        ps, pm, psmb = _small(insights, s, e, g or None), _mkt(insights, s, e, g or None), _smb(insights, s, e, g or None)
        label = f"{s}-{e}"
        row = dict(group=g, period=label, years_used=A.years_available(small_a, s, e),
                   small_paper=ps.value if ps else np.nan, small_repl=round(sm, 2),
                   mkt_paper=pm.value if pm else np.nan, mkt_repl=round(mk, 2),
                   spread_paper_bp=round((ps.value - pm.value) * 100) if ps and pm else np.nan,
                   spread_repl_bp=round((sm - mk) * 100),
                   smb_paper_bp=psmb.value if psmb else np.nan, smb_repl_bp=round(smb))
        rows.append(row)
        for c in (
            compare_to_result("ex3_small_level", sm, ps, 1.0, 2.5, f"Small stocks {label} annualized", "%"),
            compare_to_result("ex3_market_level", mk, pm, 0.75, 1.5, f"Market {label} annualized", "%"),
            compare_to_result("ex3_smb", smb, psmb, 75, 150, f"SMB {label} (mean x12)", "bp"),
        ):
            if c:
                res.checks.append(c)
        if ps and pm:
            paper_spread = (ps.value - pm.value) * 100
            res.checks.append(compare_value("ex3_spread", (sm - mk) * 100, paper_spread, 150, 300,
                                            f"Small minus market {label}", [ps.id, pm.id], "bp"))
    res.tables["exhibit3_subperiods"] = pd.DataFrame(rows)

    # ---- skewness probes -------------------------------------------------------
    our_extreme = A.extreme_years(diff_a, 4, 1926, 2023)
    probe_rows = [dict(probe="replicated top-4 small-minus-market years", years=str(our_extreme),
                       spread_repl_bp=round((A.period_annualized(small_a, 1926, 2023, our_extreme)
                                             - A.period_annualized(mkt_a, 1926, 2023, our_extreme)) * 10_000))]
    for g, excl in _excluded_sets(insights):
        sm = A.period_annualized(small_a, 1926, 2023, excl) * 100
        mk = A.period_annualized(mkt_a, 1926, 2023, excl) * 100
        ps, pm = _small(insights, 1926, 2023, None, excl), _mkt(insights, 1926, 2023, None, excl)
        paper_spread = (ps.value - pm.value) * 100 if ps and pm else np.nan
        probe_rows.append(dict(probe=g, years=str(list(excl)), spread_paper_bp=paper_spread,
                               spread_repl_bp=round((sm - mk) * 100)))
        if ps and pm:
            res.checks.append(compare_value("ex3_skew_probe", (sm - mk) * 100, paper_spread, 100, 200,
                                            f"Spread after dropping {list(excl)}", [ps.id, pm.id], "bp"))
        contiguous = list(excl) == list(range(min(excl), max(excl) + 1))
        if not contiguous:  # "most extreme years" probe rather than a contiguous era
            overlap = len(set(excl) & set(our_extreme))
            res.checks.append(CheckResult(
                check="ex3_extreme_years", status="pass" if overlap >= 3 else "warn" if overlap == 2 else "fail",
                message=f"Paper's most extreme years {list(excl)} vs replicated {our_extreme}: {overlap}/4 overlap",
                targets=[ps.id] if ps else []))
    full_spread = (A.period_annualized(small_a, 1926, 2023) - A.period_annualized(mkt_a, 1926, 2023)) * 10_000
    top4_spread = probe_rows[0]["spread_repl_bp"]
    res.checks.append(CheckResult(
        check="claim_C3_skew", status="pass" if top4_spread <= 0.25 * full_spread or top4_spread <= 25 else "warn",
        expected=0.0, observed=top4_spread,
        message=f"Dropping the 4 best small-stock years moves the full-period spread from {full_spread:.0f}bp "
                f"to {top4_spread:.0f}bp (paper: advantage disappears)"))
    res.tables["exhibit3_skewness_probes"] = pd.DataFrame(probe_rows)

    # ---- Exhibit 4: trailing 120m anti-factor ----------------------------------
    anti = A.rolling_excess(data["BIG_LoBM"], data["MKT"], window) * 100
    lv = A.rolling_excess(data["BIG_HiBM"], data["MKT"], window) * 100
    sm_roll = A.rolling_excess(data["SMALL"], data["MKT"], window) * 100
    res.tables["exhibit4_rolling_120m"] = pd.DataFrame(
        {"big_lobm_minus_mkt_pct": anti, "big_hibm_minus_mkt_pct": lv, "small_minus_mkt_pct": sm_roll})
    if not anti.empty:
        rmin, rmax = insights.result("ex4_min") if insights else None, insights.result("ex4_max") if insights else None
        for c in (compare_to_result("ex4_min", float(anti.min()), rmin, 0.75, 1.5,
                                    f"Exhibit 4 trough ({anti.idxmin()})", "%"),
                  compare_to_result("ex4_max", float(anti.max()), rmax, 0.75, 1.5,
                                    f"Exhibit 4 peak ({anti.idxmax()})", "%")):
            if c:
                res.checks.append(c)
        tmin = anti.idxmin().year
        res.checks.append(CheckResult(check="ex4_trough_timing", status="pass" if 1978 <= tmin <= 1990 else "fail",
                                      observed=tmin, message=f"Deepest anti-factor underperformance ends {anti.idxmin()} "
                                                             "(paper: decades ending early-mid 1980s)"))
        recent = anti[anti.index.year >= 2019]
        if not recent.empty:
            res.checks.append(CheckResult(
                check="ex4_recent_outperformance", status="pass" if recent.mean() > 0 else "fail",
                observed=round(float(recent.mean()), 2),
                message=f"Mean trailing-10y BIG LoBM minus market for roll ends 2019+: {recent.mean():.2f}% "
                        "(paper: significantly outperformed in the 2020s)"))

    # ---- Claim C7: large value beat market for every roll ending 1963-1990 -------
    lv_window = lv[(lv.index.year >= 1963) & (lv.index.year <= 1990)]
    if not lv_window.empty:
        frac = float((lv_window > 0).mean())
        res.checks.append(CheckResult(
            check="claim_C7_large_value_1963_1990", status="pass" if frac == 1 else "warn" if frac >= 0.9 else "fail",
            observed=round(frac, 3), expected=1.0,
            message=f"BIG HiBM beat market in {frac:.1%} of trailing-{window}m windows ending 1963-1990 "
                    f"(paper: every one); worst {lv_window.min():.2f}% at {lv_window.idxmin()}"))

    # ---- Claims C1 / C8: long-short mean > 0 yet long-only decades of loss; is it chance? ----
    rel = ((1 + data["SMALL"]) / (1 + data["MKT"]) - 1).dropna()
    smb_mean = float(data["SMB"].mean() * 12 * 10_000)
    rows = []
    for horizon in (120, 216):
        hist = A.rolling_excess(data["SMALL"], data["MKT"], horizon)
        hist_frac = float((hist < 0).mean()) if not hist.empty else np.nan
        sims = A.bootstrap_underperformance(rel, horizon, n_sims=n_sims)
        boot_p = float((sims < 0).mean())
        rows.append(dict(horizon_years=horizon / 12, hist_frac_windows_underperform=round(hist_frac, 3),
                         bootstrap_prob_underperform=round(boot_p, 3),
                         bootstrap_p5_pct=round(float(np.percentile(sims, 5)) * 100, 2),
                         bootstrap_p95_pct=round(float(np.percentile(sims, 95)) * 100, 2)))
        if horizon == 120:
            res.checks.append(CheckResult(
                check="claim_C1_decade_underperformance", status="pass" if smb_mean > 0 and hist_frac > 0.2 else "warn",
                observed=round(hist_frac, 3),
                message=f"SMB mean {smb_mean:.0f}bp/yr > 0, yet small-stock proxy trailed the market in "
                        f"{hist_frac:.0%} of trailing 10-year windows"))
        gap = abs(hist_frac - boot_p)
        res.checks.append(CheckResult(
            check="claim_C8_random_fluctuation", status="pass" if gap <= 0.15 else "warn" if gap <= 0.30 else "fail",
            expected=round(boot_p, 3), observed=round(hist_frac, 3),
            message=f"{horizon // 12}y horizon: block-bootstrap (premium held at its historical mean) gives "
                    f"P(underperform)={boot_p:.0%}; history shows {hist_frac:.0%} of windows. "
                    + ("Consistent with chance." if gap <= 0.15 else
                       "History has more/longer spells than chance implies - regimes, not just noise.")))
    res.tables["bootstrap_underperformance"] = pd.DataFrame(rows)

    if with_funds:
        res.checks += _fund_checks(insights, res)
    return res


# ---------------------------------------------------------------------------
# Exhibits 1-2 from fund NAVs (optional, needs yfinance + Yahoo access)
# ---------------------------------------------------------------------------

FUND_TESTS = [
    # (claim id, numerator, denominator, start, end, label)
    ("txt_ex1_almost_twice", "VFINX", "DFSCX", "1981-12-31", "1999-12-31", "S&P fund / DFA Microcap 1982-1999"),
    ("txt_ex1_double", "DFSCX", "VFINX", "1999-12-31", "2017-12-31", "DFA Microcap / S&P fund 2000-2017"),
    ("txt_ex2_30pct_more", "DFLVX", "VTSMX", "1993-06-30", "2007-06-30", "DFA Large Value / Total Market 1993-2007"),
    ("txt_ex2_30pct_less", "DFLVX", "VTSMX", "2007-06-30", "2021-06-30", "DFA Large Value / Total Market 2007-2021"),
]


def _fund_checks(insights: Optional[PaperInsights], res: ReplicationResult) -> list[CheckResult]:
    out: list[CheckResult] = []
    try:
        import yfinance as yf
    except Exception as e:  # pragma: no cover
        return [CheckResult(check="funds", status="skip", message=f"yfinance unavailable: {e}")]
    cache: dict[str, pd.Series] = {}
    rows = []
    for cid, num, den, start, end, label in FUND_TESTS:
        try:
            for t in (num, den):
                if t not in cache:
                    px = yf.download(t, start="1980-01-01", interval="1mo", auto_adjust=True, progress=False)["Close"]
                    cache[t] = (px.iloc[:, 0] if isinstance(px, pd.DataFrame) else px).dropna()
            a, b = cache[num], cache[den]
            s, e = pd.Timestamp(start), pd.Timestamp(end)
            if a.index.min() > s + pd.Timedelta(days=45) or b.index.min() > s + pd.Timedelta(days=45):
                out.append(CheckResult(check="fund_ratio", status="skip", targets=[cid],
                                       message=f"{label}: Yahoo history starts {min(a.index.min(), b.index.min()).date()}"
                                               f" / {max(a.index.min(), b.index.min()).date()}, after {start}"))
                continue
            ga = a.asof(e) / a.asof(s)
            gb = b.asof(e) / b.asof(s)
            ratio = float(ga / gb)
            rows.append(dict(test=label, ratio=round(ratio, 3)))
            r = insights.result(cid) if insights else None
            if r:
                out.append(compare_value("fund_ratio", ratio, r.value, 0.15 * r.value, 0.35 * r.value, label,
                                         [cid], "x"))
        except Exception as ex:  # network / ticker issues
            out.append(CheckResult(check="fund_ratio", status="skip", targets=[cid], message=f"{label}: {ex}"))
    if rows:
        res.tables["exhibit1_2_fund_ratios"] = pd.DataFrame(rows)
    return out
