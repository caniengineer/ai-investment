"""Command line entry point.

Examples
--------
  # Full analysis with the LLM (needs ANTHROPIC_API_KEY or OPENAI_API_KEY + LLM_PROVIDER)
  python -m app.paper_lab analyze paper.pdf --out reports/my_paper

  # Offline / no API key: heuristic extraction + citation + red-flag checks
  python -m app.paper_lab analyze paper.pdf --no-llm --out reports/my_paper

  # Use a curated / previously extracted insights file and replicate with public data
  python -m app.paper_lab analyze paper.pdf --insights examples/papers/mcquarrie_2025/insights.json \\
      --replicate factor-fluctuation --out reports/mcquarrie

  # Behind a firewall: put the Ken French zips in a folder and point at it
  python -m app.paper_lab analyze ... --replicate factor-fluctuation --data-dir data/french --offline

  python -m app.paper_lab recipes
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from app.paper_lab.pipeline import analyze, save
from app.paper_lab.replication import list_recipes
from app.paper_lab.schema import PaperInsights


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="paper_lab", description="Extract, audit and replicate finance papers.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    an = sub.add_parser("analyze", help="Extract insights, run legitimacy checks, optionally replicate")
    an.add_argument("paper", nargs="?", help="PDF (or .txt) of the paper")
    an.add_argument("--out", default="reports/paper", help="Output directory")
    an.add_argument("--no-llm", action="store_true", help="Heuristic extraction only (no API key needed)")
    an.add_argument("--insights", help="Use an existing insights.json instead of extracting")
    an.add_argument("--replicate", metavar="RECIPE", help="Replication recipe to run (see `recipes`)")
    an.add_argument("--data-dir", help="Folder with pre-downloaded data files (e.g. Ken French zips)")
    an.add_argument("--offline", action="store_true", help="Never download; use --data-dir / cache only")
    an.add_argument("--with-funds", action="store_true", help="Also pull mutual fund NAVs from Yahoo (recipe permitting)")

    sub.add_parser("recipes", help="List replication recipes")

    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.cmd == "recipes":
        for name, desc in list_recipes().items():
            print(f"{name:22s} {desc}")
        return 0

    if not args.paper and not args.insights:
        ap.error("analyze needs a paper path and/or --insights")
    ins = PaperInsights.model_validate_json(Path(args.insights).read_text()) if args.insights else None
    rkw = {"data_dir": args.data_dir, "offline": args.offline}
    if args.with_funds:
        rkw["with_funds"] = True
    result = analyze(args.paper, insights=ins, use_llm=not args.no_llm, recipe=args.replicate, recipe_kwargs=rkw)
    paths = save(result, args.out)

    leg = result.legitimacy
    print(f"\nOverall {leg.overall_score}/100 (rigor {leg.rigor_score}, consistency "
          f"{leg.internal_consistency_score}, replicability {leg.replicability_score})")
    print(leg.verdict)
    if result.suggested_recipes and not args.replicate:
        print(f"Suggested replication recipes: {', '.join(result.suggested_recipes)} (use --replicate)")
    print(f"Report: {paths['report']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
