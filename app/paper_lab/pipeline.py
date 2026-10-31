"""End-to-end: paper -> insights -> legitimacy checks -> (replication) -> report."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.paper_lab import checks, report
from app.paper_lab.extractor import extract
from app.paper_lab.pdf_text import PaperText, extract_text
from app.paper_lab.replication import ReplicationResult, get_recipe, suggest_recipes
from app.paper_lab.schema import LegitimacyReport, PaperInsights

logger = logging.getLogger("alphaagent.paper_lab")


@dataclass
class AnalysisResult:
    insights: PaperInsights
    legitimacy: LegitimacyReport
    report_md: str
    replication: Optional[ReplicationResult] = None
    suggested_recipes: Optional[list[str]] = None


def analyze(paper_path: Optional[str | Path] = None, *, insights: Optional[PaperInsights] = None,
            use_llm: bool = True, llm=None, recipe: Optional[str] = None,
            recipe_kwargs: Optional[dict] = None) -> AnalysisResult:
    """Run the pipeline. Pass ``insights`` to skip extraction (e.g. a curated JSON)."""
    paper: Optional[PaperText] = extract_text(paper_path) if paper_path else None
    if insights is None:
        if paper is None:
            raise ValueError("Need a paper path or insights")
        insights = extract(paper, use_llm=use_llm, llm=llm)

    repl = None
    if recipe:
        logger.info("Running replication recipe %s", recipe)
        repl = get_recipe(recipe)(insights=insights, **(recipe_kwargs or {}))

    leg = checks.assess(insights, raw_text=paper.plain_text if paper else "",
                        replication_checks=repl.checks if repl else None)
    md = report.render(insights, leg, repl)
    return AnalysisResult(insights=insights, legitimacy=leg, report_md=md, replication=repl,
                          suggested_recipes=suggest_recipes(insights))


def save(result: AnalysisResult, out_dir: str | Path) -> dict[str, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "insights": out / "insights.json",
        "legitimacy": out / "legitimacy.json",
        "report": out / "report.md",
    }
    paths["insights"].write_text(result.insights.model_dump_json(indent=2))
    paths["legitimacy"].write_text(result.legitimacy.model_dump_json(indent=2))
    paths["report"].write_text(result.report_md)
    if result.replication:
        for p in result.replication.save(out / "replication"):
            paths[p.stem] = p
        (out / "replication" / "checks.json").write_text(
            json.dumps([c.model_dump() for c in result.replication.checks], indent=2))
    return paths
