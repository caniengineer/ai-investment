"""Legitimacy checks that need no market data.

1. Internal arithmetic consistency
   - derived numbers (spreads, ratios, terminal-wealth multiples) match their inputs
   - sub-period annualized returns compound to the full-period figure
   - "years" columns match the stated periods
2. Citation hygiene - in-text (Author Year) vs the reference list
3. Methodology red flags - costs, significance, out-of-sample, data access, ...
4. Scores + verdict
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Iterable, Optional

from app.paper_lab.schema import (
    CheckResult,
    LegitimacyReport,
    NumericResult,
    PaperInsights,
    RedFlag,
)

SEVERITY_PENALTY = {"high": 20, "medium": 12, "low": 5, "info": 0}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _half_unit(x: float) -> float:
    """Half of the last reported digit: 11.83 -> 0.005, 798 -> 0.5, 19.5 -> 0.05."""
    s = repr(float(x))
    if "e" in s:
        return 0.0
    dec = s.split(".")[1].rstrip("0") if "." in s else ""
    return 0.5 * 10 ** (-len(dec))


def _as_fraction(r: NumericResult) -> float:
    if r.unit == "percent":
        return r.value / 100.0
    if r.unit == "bp":
        return r.value / 10_000.0
    return r.value


def _compare(expected: float, reported: NumericResult, tol: float) -> tuple[str, float]:
    """Return (status, diff) comparing an expected value against a reported one."""
    v = reported.value
    diff = expected - v
    c = reported.comparator
    if c == "approx":
        tol = max(tol, 0.10 * abs(v))
    if c in ("gt", "gte"):
        ok = expected >= v - tol
    elif c in ("lt", "lte"):
        ok = expected <= v + tol
    else:
        ok = abs(diff) <= tol
    if ok:
        return "pass", diff
    close = abs(diff) <= max(3 * tol, 0.05 * abs(v))
    return ("warn" if close else "fail"), diff


# ---------------------------------------------------------------------------
# 1. internal consistency
# ---------------------------------------------------------------------------


def check_derivations(ins: PaperInsights) -> list[CheckResult]:
    out: list[CheckResult] = []
    for r in ins.numeric_results:
        d = r.derivation
        if not d:
            continue
        ops = [ins.result(i) for i in d.operands]
        if any(o is None for o in ops):
            out.append(CheckResult(check="derivation", status="skip", targets=[r.id],
                                   message=f"{r.id}: unknown operand ids {d.operands}"))
            continue
        try:
            if d.op == "difference":
                a, b = ops[0], ops[1]
                diff_frac = _as_fraction(a) - _as_fraction(b)
                expected = diff_frac * (10_000 if r.unit == "bp" else 100 if r.unit == "percent" else 1)
                scale = 10_000 if r.unit == "bp" else 100 if r.unit == "percent" else 1
                in_scale = 100 if a.unit == "percent" else 10_000 if a.unit == "bp" else 1
                tol = (_half_unit(a.value) + _half_unit(b.value)) * scale / in_scale + _half_unit(r.value)
            elif d.op == "sum":
                expected = sum(o.value for o in ops)
                tol = sum(_half_unit(o.value) for o in ops) + _half_unit(r.value)
            elif d.op == "ratio":
                a, b = ops[0].value, ops[1].value
                expected = a / b
                tol = expected * (_half_unit(a) / abs(a) + _half_unit(b) / abs(b)) + _half_unit(r.value)
            elif d.op == "wealth_ratio":
                years = d.years or ((ops[0].period_end - ops[0].period_start + 1)
                                    if ops[0].period_start and ops[0].period_end else None)
                if not years:
                    raise ValueError("wealth_ratio needs years")
                a, b = _as_fraction(ops[0]), _as_fraction(ops[1])
                expected = ((1 + a) / (1 + b)) ** years
                ha = _half_unit(ops[0].value) / (100 if ops[0].unit == "percent" else 1)
                tol = expected * years * 2 * ha + _half_unit(r.value)
            else:  # pragma: no cover
                continue
        except (ZeroDivisionError, ValueError, TypeError) as e:
            out.append(CheckResult(check="derivation", status="skip", targets=[r.id], message=f"{r.id}: {e}"))
            continue
        status, diff = _compare(expected, r, tol)
        out.append(CheckResult(
            check="derivation", status=status, expected=round(expected, 4), observed=r.value,
            targets=[r.id, *d.operands],
            message=f"{r.series} ({r.source or r.id}): reported {r.comparator} {r.value:g} {r.unit}; "
                    f"{d.op} of {', '.join(d.operands)} gives {expected:.4g}"))
    return out


def _chains(full: NumericResult, pool: list[NumericResult]) -> Optional[list[NumericResult]]:
    """Find contiguous non-overlapping periods in pool exactly covering full's period."""
    by_start: dict[int, list[NumericResult]] = defaultdict(list)
    for p in pool:
        by_start[p.period_start].append(p)

    def dfs(cur: int, acc: list[NumericResult]) -> Optional[list[NumericResult]]:
        if cur == full.period_end + 1:
            return acc
        for p in sorted(by_start.get(cur, []), key=lambda x: -(x.period_end or 0)):
            if p.period_end <= full.period_end:
                found = dfs(p.period_end + 1, acc + [p])
                if found:
                    return found
        return None

    chain = dfs(full.period_start, [])
    return chain if chain and len(chain) > 1 else None


def check_compounding(ins: PaperInsights, metric: str = "annualized_return") -> list[CheckResult]:
    out: list[CheckResult] = []
    rows = [r for r in ins.numeric_results
            if r.metric == metric and r.period_start and r.period_end and not r.excluded_years
            and r.unit == "percent" and r.comparator in ("eq", "approx")]
    by_series: dict[str, list[NumericResult]] = defaultdict(list)
    for r in rows:
        by_series[r.series.strip().lower()].append(r)

    for series_rows in by_series.values():
        for full in series_rows:
            groups: dict[Optional[str], list[NumericResult]] = defaultdict(list)
            for r in series_rows:
                if r is not full and full.period_start <= r.period_start and r.period_end <= full.period_end:
                    groups[r.group].append(r)
            for group, pool in groups.items():
                if group is not None and group == full.group:
                    continue
                chain = _chains(full, pool)
                if not chain:
                    continue
                n = sum(p.period_end - p.period_start + 1 for p in chain)
                geo = math.exp(sum((p.period_end - p.period_start + 1) * math.log(1 + p.value / 100)
                                   for p in chain) / n) - 1
                arith = sum((p.period_end - p.period_start + 1) * p.value / 100 for p in chain) / n
                # Table columns share one precision: use the finest digit seen in the chain
                # (10.0% is stored as 10.0 and would otherwise look like an integer).
                tol = min(_half_unit(p.value) for p in chain) + _half_unit(full.value) + 0.02
                geo_pct, ari_pct = geo * 100, arith * 100
                gap = full.value - geo_pct
                note = ""
                if abs(gap) <= tol:
                    status = "pass"
                elif abs(ari_pct - full.value) <= tol:
                    status, note = "pass", " (matches arithmetic mean of annual returns, not compounded)"
                elif abs(gap) <= 3 * tol:
                    status = "warn"
                else:
                    status = "fail"
                periods = ", ".join(f"{p.period_start}-{p.period_end}:{p.value:g}%" for p in chain)
                out.append(CheckResult(
                    check="compounding", status=status, expected=round(geo_pct, 3), observed=full.value,
                    targets=[full.id] + [p.id for p in chain],
                    message=f"{full.series} {full.period_start}-{full.period_end} reported {full.value:g}%; "
                            f"compounding sub-periods [{group or 'ungrouped'}: {periods}] gives "
                            f"{geo_pct:.2f}% (arith {ari_pct:.2f}%), gap {gap * 100:+.0f} bp{note}"))
    return out


def check_period_lengths(ins: PaperInsights) -> list[CheckResult]:
    out = []
    for r in ins.numeric_results:
        if r.metric == "years" and r.period_start and r.period_end:
            expected = r.period_end - r.period_start + 1 - len(r.excluded_years)
            status = "pass" if expected == r.value else "fail"
            out.append(CheckResult(check="period_length", status=status, expected=expected, observed=r.value,
                                   targets=[r.id],
                                   message=f"{r.id}: {r.period_start}-{r.period_end} minus "
                                           f"{len(r.excluded_years)} excluded = {expected} years, reported {r.value:g}"))
    return out


# ---------------------------------------------------------------------------
# 2. citations
# ---------------------------------------------------------------------------

_STOP = {"Exhibit", "Table", "Figure", "Section", "June", "Since", "From", "In", "The", "Over", "After",
         "Before", "World", "War", "Fund", "Value", "Index", "Panel", "Appendix", "Through", "Until", "Of"} | {
    m for m in ("January February March April May July August September October November December".split())}
_SURNAME = r"[A-Z][a-zA-Z'\-]+"
_AUTH = rf"(?:(?:van|von|de|der|da|di|le)\s+)*{_SURNAME}"
_INTEXT_RE = re.compile(
    rf"\b({_SURNAME})(?:\s+et\s+al\.?|\s+and\s+{_AUTH}"
    rf"|(?:,\s*{_AUTH})+,?\s+(?:and|&)\s+{_AUTH}|,\s+{_AUTH})?\s*(?:’s|'s)?\s*\(?((?:19|20)\d{{2}})[a-z]?\)?")


def _all_authors(entry: str) -> set[str]:
    head = re.split(r"\b(?:19|20)\d{2}\b", entry, maxsplit=1)[0]
    return set(re.findall(rf"({_SURNAME}),\s+[A-Z](?:\.|[A-Z]{{0,2}}\b)", head)) | set(
        re.findall(rf"(?:and|&)\s+(?:[A-Z][a-z]+\s+(?:[A-Z]\.\s*)*)?({_SURNAME})", head))


def parse_references(text: str) -> list[tuple[str, Optional[int], str]]:
    m = list(re.finditer(r"^\s*(REFERENCES|References|Bibliography|BIBLIOGRAPHY)\s*$", text, re.M))
    if not m:
        return []
    block = text[m[-1].end():]
    starts = list(re.finditer(rf"^\s*({_SURNAME}),\s+(?:[A-Z]\.|[A-Z]{{1,3}}\b|[A-Z][a-z]+)", block, re.M))
    refs = []
    for i, s in enumerate(starts):
        entry = block[s.start(): starts[i + 1].start() if i + 1 < len(starts) else len(block)]
        entry = re.sub(r"\s+", " ", entry).strip()
        y = re.search(r"\b((?:19|20)\d{2})\b", entry)
        refs.append((s.group(1), int(y.group(1)) if y else None, entry[:200]))
    return refs


def check_citations(text: str) -> tuple[list[CheckResult], list[RedFlag]]:
    refs = parse_references(text)
    if not refs:
        return [CheckResult(check="citations", status="skip", message="No reference list found")], []
    ref_idx = re.search(r"^\s*(REFERENCES|References|Bibliography|BIBLIOGRAPHY)\s*$", text, re.M)
    body = text[: ref_idx.start()] if ref_idx else text
    body = re.sub(r"\s+", " ", body)

    ref_years: dict[str, set[int]] = defaultdict(set)
    coauthor_years: dict[str, set[int]] = defaultdict(set)
    for name, year, entry in refs:
        if year:
            ref_years[name].add(year)
            for a in _all_authors(entry):
                coauthor_years[a].add(year)

    cited: dict[tuple[str, int], str] = {}
    for m in _INTEXT_RE.finditer(body):
        name, year = m.group(1), int(m.group(2))
        if name in _STOP:
            continue
        cited.setdefault((name, year), m.group(0))

    checks: list[CheckResult] = []
    flags: list[RedFlag] = []
    for (name, year), raw in sorted(cited.items()):
        if year in coauthor_years.get(name, ()):
            continue
        if name in ref_years:
            if year in ref_years[name]:
                continue
            msg = f"In-text '{raw.strip()}' but reference list has {name} {sorted(ref_years[name])}"
            checks.append(CheckResult(check="citation_year", status="warn", message=msg, targets=[name]))
            flags.append(RedFlag(code="CITATION_MISMATCH", severity="low", message=msg, source="citations"))
        elif re.search(rf"\({name}\b|\b{name}\s*(?:et al\.?)?\s*\(\d{{4}}", body) or re.search(rf"\b{name} et al", raw):
            msg = f"'{raw.strip()}' cited but not in reference list"
            checks.append(CheckResult(check="citation_missing", status="warn", message=msg, targets=[name]))
            flags.append(RedFlag(code="CITATION_MISSING", severity="low", message=msg, source="citations"))

    cited_names = {n for n, _ in cited}
    uncited = [f"{n} {y}" for n, y, _ in refs if n not in cited_names]
    if uncited:
        checks.append(CheckResult(check="citation_uncited", status="warn",
                                  message="References never cited in text: " + ", ".join(uncited)))
    n_bad = sum(1 for c in checks if c.check != "citation_uncited")
    checks.insert(0, CheckResult(check="citations", status="pass" if n_bad == 0 else "warn",
                                 message=f"{len(refs)} references, {len(cited)} in-text citations, "
                                         f"{n_bad} inconsistencies"))
    return checks, flags


# ---------------------------------------------------------------------------
# 3. methodology red flags
# ---------------------------------------------------------------------------


def methodology_flags(ins: PaperInsights) -> list[RedFlag]:
    m = ins.methodology
    f: list[RedFlag] = []

    def add(code, sev, msg, ev=""):
        f.append(RedFlag(code=code, severity=sev, message=msg, evidence=ev, source="heuristic"))

    if m.transaction_costs_modeled is not True:
        sev = "high" if m.long_short else "medium"
        add("NO_TRANSACTION_COSTS", sev, "Results are not shown net of transaction costs / bid-ask spreads"
            + (" (long-short factor returns)" if m.long_short else "") + ".")
    if m.long_short:
        add("LONG_SHORT_PAPER_RETURNS", "medium",
            "Evidence relies on long-short paper portfolios; long-only implementation may differ materially.")
    if m.significance_reported is not True:
        add("NO_SIGNIFICANCE_TESTS", "medium",
            "No t-statistics / p-values / confidence intervals reported for the headline differences.")
    if m.out_of_sample_test is not True:
        add("NO_OUT_OF_SAMPLE", "medium", "No explicit out-of-sample or hold-out validation.")
    if m.sample_years is not None and m.sample_years < 10:
        add("SHORT_SAMPLE", "high", f"Sample covers only {m.sample_years:g} years.")
    elif m.sample_years is not None and m.sample_years < 20:
        add("SHORT_SAMPLE", "medium", f"Sample covers {m.sample_years:g} years; regime dependence likely.")
    if (m.n_strategies_tested or 0) > 5 and not m.multiple_testing_adjustment:
        add("MULTIPLE_TESTING", "high",
            f"{m.n_strategies_tested} strategies/specifications tested without a multiple-testing adjustment "
            "(Harvey-Liu-Zhu t>3 hurdle).")
    if m.survivorship_bias_addressed is not True:
        add("SURVIVORSHIP_UNADDRESSED", "low", "Survivorship / delisting bias is not discussed.")
    if m.lookahead_bias_addressed is not True and (m.portfolio_construction or m.long_short):
        add("LOOKAHEAD_UNADDRESSED", "low", "Look-ahead / reporting-lag handling is not stated.")
    if not m.robustness_checks:
        add("NO_ROBUSTNESS", "low", "No robustness checks (alternative periods, definitions, weights) listed.")
    if not m.statistical_tests:
        add("DESCRIPTIVE_ONLY", "info", "Evidence is descriptive (no formal statistical tests).")
    closed = [d for d in ins.datasets if d.public is False]
    for d in closed:
        sev = "low" if d.substitute else "medium"
        add("PROPRIETARY_DATA", sev, f"Uses proprietary data: {d.name}.",
            f"Public substitute: {d.substitute}" if d.substitute else "No public substitute identified.")
    return f


# ---------------------------------------------------------------------------
# 4. scoring
# ---------------------------------------------------------------------------


def _clamp(x: float) -> int:
    return int(max(0, min(100, round(x))))


def replicability_score(ins: PaperInsights) -> int:
    s = 100.0
    for d in ins.datasets:
        if d.public is False:
            s -= 10 if d.substitute else 25
    m = ins.methodology
    if not m.portfolio_construction:
        s -= 15
    if not m.rebalancing:
        s -= 10
    if not m.sample_period:
        s -= 10
    if not ins.datasets:
        s -= 20
    rep = [e.replicable for e in ins.exhibits if e.replicable is not None]
    if rep:
        s -= 30 * (1 - sum(rep) / len(rep))
    return _clamp(s)


def consistency_score(checks: Iterable[CheckResult]) -> int:
    """Diminishing penalty: inconsistencies in one table are usually correlated."""
    penalty = 0.0
    for c in checks:
        if c.check in ("citation_year", "citation_missing"):
            penalty += 3
        elif not c.check.startswith("citation"):
            penalty += {"fail": 15, "warn": 6}.get(c.status, 0)
    return _clamp(100 * math.exp(-penalty / 100))


def verdict_for(score: int) -> str:
    if score >= 80:
        return "Credible: results are internally consistent and methodology is sound; replicate before trading."
    if score >= 60:
        return "Plausible with caveats: core findings likely hold but specific numbers/claims need verification."
    if score >= 40:
        return "Weak: material methodological gaps or inconsistencies; do not trade without independent replication."
    return "Not credible as stated: serious inconsistencies or untestable claims."


def assess(ins: PaperInsights, raw_text: str = "",
           replication_checks: Optional[list[CheckResult]] = None) -> LegitimacyReport:
    checks = check_period_lengths(ins) + check_derivations(ins) + check_compounding(ins)
    flags = list(ins.red_flags) + methodology_flags(ins)

    for c in checks:
        if c.status == "fail":
            flags.append(RedFlag(code="INTERNAL_INCONSISTENCY", severity="medium", message=c.message,
                                 source="consistency"))
        elif c.status == "warn":
            flags.append(RedFlag(code="ROUNDING_OR_INCONSISTENCY", severity="low", message=c.message,
                                 source="consistency"))

    if raw_text:
        cchecks, cflags = check_citations(raw_text)
        checks += cchecks
        flags += cflags

    # duplicate codes (e.g. heuristic + LLM both flag missing costs) count once
    seen, penalty = set(), 0
    for f in flags:
        if f.source in ("heuristic", "llm") and f.code not in seen:
            seen.add(f.code)
            penalty += SEVERITY_PENALTY[f.severity]
    rigor = _clamp(100 * math.exp(-penalty / 100))
    repl = replicability_score(ins)
    cons = consistency_score(checks)
    overall = 0.35 * rigor + 0.35 * cons + 0.30 * repl

    if replication_checks:
        decided = [c for c in replication_checks if c.status in ("pass", "warn", "fail")]
        if decided:
            rep_score = 100 * sum({"pass": 1, "warn": 0.5, "fail": 0}[c.status] for c in decided) / len(decided)
            overall = 0.25 * rigor + 0.25 * cons + 0.15 * repl + 0.35 * rep_score
            for c in decided:
                if c.status == "fail":
                    flags.append(RedFlag(code="REPLICATION_FAILED", severity="high", message=c.message,
                                         source="replication"))
        checks += replication_checks

    overall_i = _clamp(overall)
    return LegitimacyReport(replicability_score=repl, rigor_score=rigor, internal_consistency_score=cons,
                            overall_score=overall_i, verdict=verdict_for(overall_i), checks=checks,
                            red_flags=flags)
