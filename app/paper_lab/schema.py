"""Structured representation of what a research paper claims.

Everything the Paper Lab does flows through ``PaperInsights``: the LLM (or the
heuristic extractor) fills it in, the legitimacy checks read it, and the
replication recipes compare their own numbers against the ``numeric_results``
recorded here.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Unit = Literal["percent", "bp", "dollars", "ratio", "multiple", "years", "count", "other"]
Comparator = Literal["eq", "approx", "gt", "lt", "gte", "lte"]
Severity = Literal["info", "low", "medium", "high"]


class PaperMetadata(BaseModel):
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    identifier: Optional[str] = Field(None, description="DOI, SSRN id, arXiv id, ...")
    pages: Optional[int] = None


class Claim(BaseModel):
    """A qualitative/quantitative assertion the paper makes."""

    id: str
    statement: str
    kind: Literal["main_thesis", "empirical", "methodological", "interpretive", "recommendation"] = "empirical"
    evidence: str = Field("", description="Which exhibit / test supports it")
    page: Optional[int] = None
    testable: bool = True
    how_to_test: str = ""


class Derivation(BaseModel):
    """How a reported number should follow from other reported numbers.

    ops:
      difference      value = a - b          (unit conversion % -> bp handled)
      ratio           value = a / b
      wealth_ratio    value = ((1+a)/(1+b)) ** years   (a, b annualized returns)
      sum             value = sum(operands)
    """

    op: Literal["difference", "ratio", "wealth_ratio", "sum"]
    operands: list[str]
    years: Optional[float] = None


class NumericResult(BaseModel):
    """A single number reported in a table, figure label or the text."""

    id: str
    series: str = Field(..., description="What is measured, e.g. 'Small Stocks', 'SMB', 'DFA Large Value'")
    metric: str = Field(..., description="e.g. annualized_return, excess_return, terminal_wealth, wealth_ratio, years")
    value: float
    unit: Unit = "percent"
    comparator: Comparator = "eq"
    period_start: Optional[int] = None
    period_end: Optional[int] = None
    group: Optional[str] = Field(None, description="Table panel, e.g. 'six_period' - used for consistency checks")
    excluded_years: list[int] = Field(default_factory=list)
    source: str = ""
    page: Optional[int] = None
    quote: Optional[str] = None
    derivation: Optional[Derivation] = None


class Dataset(BaseModel):
    name: str
    provider: str = ""
    description: str = ""
    period: str = ""
    frequency: str = ""
    public: Optional[bool] = None
    url: Optional[str] = None
    access_notes: str = ""
    substitute: str = Field("", description="Public substitute if the data is proprietary")


class Methodology(BaseModel):
    research_question: str = ""
    asset_universe: str = ""
    sample_period: str = ""
    sample_years: Optional[float] = None
    frequency: str = ""
    portfolio_construction: str = ""
    weighting: str = ""
    rebalancing: str = ""
    benchmark: str = ""
    long_short: Optional[bool] = None
    transaction_costs_modeled: Optional[bool] = None
    fees_included: Optional[bool] = None
    statistical_tests: list[str] = Field(default_factory=list)
    significance_reported: Optional[bool] = None
    out_of_sample_test: Optional[bool] = None
    robustness_checks: list[str] = Field(default_factory=list)
    n_strategies_tested: Optional[int] = None
    multiple_testing_adjustment: Optional[bool] = None
    survivorship_bias_addressed: Optional[bool] = None
    lookahead_bias_addressed: Optional[bool] = None
    key_formulas: list[str] = Field(default_factory=list)
    notes: str = ""


class Exhibit(BaseModel):
    id: str
    title: str = ""
    kind: Literal["table", "figure", "other"] = "figure"
    page: Optional[int] = None
    what_it_shows: str = ""
    data_used: list[str] = Field(default_factory=list)
    replicable: Optional[bool] = None
    replication_notes: str = ""


class ReplicationStep(BaseModel):
    order: int
    action: str
    data: list[str] = Field(default_factory=list)
    output: str = ""
    targets: list[str] = Field(default_factory=list, description="ids of NumericResults / Claims this reproduces")


class RedFlag(BaseModel):
    code: str
    severity: Severity = "medium"
    message: str
    evidence: str = ""
    source: Literal["llm", "heuristic", "consistency", "citations", "replication"] = "heuristic"


class Citation(BaseModel):
    first_author: str
    year: Optional[int] = None
    raw: str = ""


class PaperInsights(BaseModel):
    metadata: PaperMetadata = Field(default_factory=PaperMetadata)
    summary: str = ""
    thesis: str = ""
    key_takeaways: list[str] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    numeric_results: list[NumericResult] = Field(default_factory=list)
    datasets: list[Dataset] = Field(default_factory=list)
    methodology: Methodology = Field(default_factory=Methodology)
    exhibits: list[Exhibit] = Field(default_factory=list)
    replication_plan: list[ReplicationStep] = Field(default_factory=list)
    red_flags: list[RedFlag] = Field(default_factory=list)
    trading_ideas: list[str] = Field(default_factory=list, description="Strategies a model could be built around")
    open_questions: list[str] = Field(default_factory=list)
    extraction_method: Literal["llm", "heuristic", "manual"] = "heuristic"

    def result(self, rid: str) -> Optional[NumericResult]:
        for r in self.numeric_results:
            if r.id == rid:
                return r
        return None


class CheckResult(BaseModel):
    """Outcome of one automated check (consistency, citation, replication)."""

    check: str
    status: Literal["pass", "warn", "fail", "skip"]
    message: str
    expected: Optional[float] = None
    observed: Optional[float] = None
    targets: list[str] = Field(default_factory=list)


class LegitimacyReport(BaseModel):
    replicability_score: int = Field(..., ge=0, le=100)
    rigor_score: int = Field(..., ge=0, le=100)
    internal_consistency_score: int = Field(..., ge=0, le=100)
    overall_score: int = Field(..., ge=0, le=100)
    verdict: str
    checks: list[CheckResult] = Field(default_factory=list)
    red_flags: list[RedFlag] = Field(default_factory=list)
