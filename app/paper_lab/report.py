"""Markdown report: insights + legitimacy scorecard + replication results."""

from __future__ import annotations

from typing import Optional

from app.paper_lab.replication import ReplicationResult
from app.paper_lab.schema import LegitimacyReport, PaperInsights

ICON = {"pass": "PASS", "warn": "WARN", "fail": "FAIL", "skip": "skip"}
SEV_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


def _yn(v: Optional[bool]) -> str:
    return "yes" if v is True else "no" if v is False else "not stated"


def _esc(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def render(ins: PaperInsights, leg: LegitimacyReport, repl: Optional[ReplicationResult] = None) -> str:
    m, md = ins.metadata, ins.methodology
    L: list[str] = []
    a = L.append
    a(f"# Paper Lab report: {m.title or 'Untitled'}")
    a("")
    a(f"*{', '.join(m.authors) or 'Unknown authors'}* · {m.year or ''} · {m.venue or ''} · {m.identifier or ''} "
      f"· extraction: **{ins.extraction_method}**")
    a("")
    a("## Scorecard")
    a("")
    a("| Overall | Rigor | Internal consistency | Replicability |")
    a("|---|---|---|---|")
    a(f"| **{leg.overall_score}/100** | {leg.rigor_score} | {leg.internal_consistency_score} | {leg.replicability_score} |")
    a("")
    a(f"**Verdict:** {leg.verdict}")
    a("")
    counts = {s: sum(1 for c in leg.checks if c.status == s) for s in ("pass", "warn", "fail", "skip")}
    a(f"Automated checks: {counts['pass']} pass · {counts['warn']} warn · {counts['fail']} fail · {counts['skip']} skipped")
    a("")

    a("## Summary")
    a("")
    if ins.thesis:
        a(f"**Thesis.** {ins.thesis}")
        a("")
    if ins.summary:
        a(ins.summary)
        a("")
    if ins.key_takeaways:
        a("**Key takeaways (as stated by the authors)**")
        a("")
        for t in ins.key_takeaways:
            a(f"- {t}")
        a("")

    if ins.claims:
        a("## Claims")
        a("")
        a("| id | kind | claim | evidence | how to test |")
        a("|---|---|---|---|---|")
        for c in ins.claims:
            a(f"| {c.id} | {c.kind} | {_esc(c.statement)} | {_esc(c.evidence)} | {_esc(c.how_to_test) if c.testable else '(not testable)'} |")
        a("")

    a("## Methodology spec (for rebuilding the model)")
    a("")
    for label, val in [
        ("Research question", md.research_question), ("Universe", md.asset_universe),
        ("Sample", f"{md.sample_period} ({md.sample_years:g} yrs)" if md.sample_years else md.sample_period),
        ("Frequency", md.frequency), ("Portfolio construction", md.portfolio_construction),
        ("Weighting", md.weighting), ("Rebalancing", md.rebalancing), ("Benchmark", md.benchmark),
        ("Long-short", _yn(md.long_short)), ("Transaction costs modeled", _yn(md.transaction_costs_modeled)),
        ("Fees included", _yn(md.fees_included)),
        ("Statistical tests", ", ".join(md.statistical_tests) or "none"),
        ("Significance reported", _yn(md.significance_reported)),
        ("Out-of-sample test", _yn(md.out_of_sample_test)),
        ("Robustness checks", "; ".join(md.robustness_checks) or "none"),
        ("Strategies tested", md.n_strategies_tested if md.n_strategies_tested is not None else "not stated"),
        ("Survivorship bias addressed", _yn(md.survivorship_bias_addressed)),
        ("Look-ahead bias addressed", _yn(md.lookahead_bias_addressed)),
    ]:
        if val not in ("", None):
            a(f"- **{label}:** {val}")
    if md.key_formulas:
        a("- **Formulas:**")
        for f in md.key_formulas:
            a(f"  - `{f}`")
    if md.notes:
        a(f"- **Notes:** {md.notes}")
    a("")

    if ins.datasets:
        a("## Data")
        a("")
        a("| dataset | public | period | access / substitute |")
        a("|---|---|---|---|")
        for d in ins.datasets:
            access = d.url or d.access_notes
            if d.public is False:
                access = f"proprietary. Substitute: {d.substitute or 'none identified'}"
            a(f"| {_esc(d.name)} | {_yn(d.public)} | {d.period} | {_esc(access)} |")
        a("")

    if ins.exhibits:
        a("## Exhibits")
        a("")
        a("| exhibit | p. | shows | replicable | notes |")
        a("|---|---|---|---|---|")
        for e in ins.exhibits:
            a(f"| {e.id}: {_esc(e.title)} | {e.page or ''} | {_esc(e.what_it_shows)} | {_yn(e.replicable)} | {_esc(e.replication_notes)} |")
        a("")

    if ins.replication_plan:
        a("## Replication plan")
        a("")
        for s in sorted(ins.replication_plan, key=lambda x: x.order):
            tgt = f" → reproduces `{', '.join(s.targets)}`" if s.targets else ""
            a(f"{s.order}. {s.action}{tgt}")
        a("")

    a("## Red flags")
    a("")
    if not leg.red_flags:
        a("None found.")
    for f in sorted(leg.red_flags, key=lambda f: (SEV_ORDER[f.severity], f.code)):
        ev = f" — {f.evidence}" if f.evidence else ""
        a(f"- **[{f.severity.upper()}] {f.code}** ({f.source}): {f.message}{ev}")
    a("")

    a("## Automated checks")
    a("")
    for title, pred in [
        ("Internal consistency (numbers vs. each other)", lambda c: c.check in ("derivation", "compounding", "period_length")),
        ("Citations", lambda c: c.check.startswith("citation")),
        ("Replication vs. public data", lambda c: not (c.check in ("derivation", "compounding", "period_length")
                                                     or c.check.startswith("citation"))),
    ]:
        rows = [c for c in leg.checks if pred(c)]
        if not rows:
            continue
        a(f"### {title}")
        a("")
        order = {"fail": 0, "warn": 1, "pass": 2, "skip": 3}
        for c in sorted(rows, key=lambda c: order[c.status]):
            a(f"- `{ICON[c.status]}` **{c.check}** — {c.message}")
        a("")

    if repl:
        a("## Replication output")
        a("")
        for n in repl.notes:
            a(f"> {n}")
            a("")
        for name, df in repl.tables.items():
            if name == "exhibit4_rolling_120m":
                a(f"**{name}**: {len(df)} monthly rows (saved to `{name}.csv`).")
                a("")
                continue
            a(f"**{name}**")
            a("")
            a(df.to_markdown(index=False) if hasattr(df, "to_markdown") and _has_tabulate() else
              "```\n" + df.to_string(index=False) + "\n```")
            a("")

    if ins.trading_ideas:
        a("## Model / strategy ideas")
        a("")
        for t in ins.trading_ideas:
            a(f"- {t}")
        a("")
    if ins.open_questions:
        a("## Open questions for replication")
        a("")
        for q in ins.open_questions:
            a(f"- {q}")
        a("")
    return "\n".join(L)


def _has_tabulate() -> bool:
    try:
        import tabulate  # noqa: F401
        return True
    except ImportError:
        return False
