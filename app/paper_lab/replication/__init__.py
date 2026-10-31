"""Replication engine: recipes rebuild a paper's exhibits from public data and
compare them, number by number, with what the paper reported."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from app.paper_lab.schema import CheckResult, NumericResult, PaperInsights


@dataclass
class ReplicationResult:
    recipe: str
    checks: list[CheckResult] = field(default_factory=list)
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def save(self, out_dir: str | Path) -> list[Path]:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        paths = []
        for name, df in self.tables.items():
            p = out / f"{name}.csv"
            df.to_csv(p)
            paths.append(p)
        return paths


def compare_value(check: str, observed: float, expected: float, pass_tol: float, warn_tol: float,
                  label: str, targets: Optional[list[str]] = None, unit: str = "") -> CheckResult:
    if observed != observed:  # NaN
        return CheckResult(check=check, status="skip", message=f"{label}: no data", expected=expected,
                           targets=targets or [])
    gap = observed - expected
    status = "pass" if abs(gap) <= pass_tol else "warn" if abs(gap) <= warn_tol else "fail"
    return CheckResult(check=check, status=status, expected=round(expected, 4), observed=round(observed, 4),
                       targets=targets or [],
                       message=f"{label}: paper {expected:.2f}{unit}, replicated {observed:.2f}{unit} "
                               f"(gap {gap:+.2f}{unit}; pass <= {pass_tol:g}, warn <= {warn_tol:g})")


def compare_to_result(check: str, observed: float, r: Optional[NumericResult], pass_tol: float,
                      warn_tol: float, label: str, unit: str = "") -> Optional[CheckResult]:
    if r is None:
        return None
    return compare_value(check, observed, r.value, pass_tol, warn_tol, label, [r.id], unit)


Recipe = Callable[..., ReplicationResult]


def _registry() -> dict[str, tuple[Recipe, str]]:
    from app.paper_lab.replication.recipes import factor_fluctuation

    return {
        "factor-fluctuation": (factor_fluctuation.run, factor_fluctuation.DESCRIPTION),
    }


def list_recipes() -> dict[str, str]:
    return {k: v[1] for k, v in _registry().items()}


def get_recipe(name: str) -> Recipe:
    reg = _registry()
    if name not in reg:
        raise KeyError(f"Unknown recipe {name!r}. Available: {', '.join(reg)}")
    return reg[name][0]


def suggest_recipes(ins: PaperInsights) -> list[str]:
    """Pick recipes whose data/method the paper uses."""
    text = " ".join([ins.summary, ins.thesis, ins.methodology.portfolio_construction,
                     " ".join(d.name for d in ins.datasets), " ".join(c.statement for c in ins.claims)]).lower()
    out = []
    if ("french" in text or "fama" in text) and any(k in text for k in ("size", "value", "smb", "hml", "small")):
        out.append("factor-fluctuation")
    return out
