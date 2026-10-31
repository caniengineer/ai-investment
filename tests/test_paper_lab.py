"""Tests for the Paper Lab (paper -> insights -> legitimacy checks -> replication)."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.paper_lab import checks
from app.paper_lab.extractor import _parse_json_object, heuristic_extract, llm_extract
from app.paper_lab.pdf_text import PaperText
from app.paper_lab.pipeline import analyze, save
from app.paper_lab.replication import analytics as A
from app.paper_lab.replication import french, suggest_recipes
from app.paper_lab.replication.recipes import factor_fluctuation
from app.paper_lab.schema import Derivation, NumericResult, PaperInsights

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "papers" / "mcquarrie_2025" / "insights.json"


@pytest.fixture
def example_insights() -> PaperInsights:
    return PaperInsights.model_validate_json(EXAMPLE.read_text())


def _r(id, value, unit="percent", **kw):
    return NumericResult(id=id, series=kw.pop("series", "S"), metric=kw.pop("metric", "annualized_return"),
                         value=value, unit=unit, **kw)


# ---------------------------------------------------------------------------
# consistency checks
# ---------------------------------------------------------------------------


class TestConsistency:
    def test_difference_in_bp(self):
        ins = PaperInsights(numeric_results=[
            _r("a", 11.83), _r("b", 10.22),
            _r("d", 161, "bp", metric="excess_return", derivation=Derivation(op="difference", operands=["a", "b"])),
            _r("bad", 200, "bp", metric="excess_return", derivation=Derivation(op="difference", operands=["a", "b"])),
        ])
        res = {c.targets[0]: c.status for c in checks.check_derivations(ins)}
        assert res == {"d": "pass", "bad": "fail"}

    def test_wealth_ratio_gt(self):
        ins = PaperInsights(numeric_results=[
            _r("a", 11.83), _r("b", 10.22),
            _r("w", 4, "multiple", comparator="gt",
               derivation=Derivation(op="wealth_ratio", operands=["a", "b"], years=98)),
        ])
        [c] = checks.check_derivations(ins)
        assert c.status == "pass" and abs(c.expected - 4.142) < 0.01

    def test_compounding_detects_gap(self):
        ins = PaperInsights(numeric_results=[
            _r("full", 9.90, period_start=2000, period_end=2009, group="all"),
            _r("p1", 5.25, period_start=2000, period_end=2004, group="split"),
            _r("p2", 14.75, period_start=2005, period_end=2009, group="split"),
        ])
        [c] = checks.check_compounding(ins)
        assert c.status == "pass"  # sqrt(1.0525 * 1.1475) - 1 = 9.90%
        ins.numeric_results[0].value = 10.50
        [c] = checks.check_compounding(ins)
        assert c.status == "fail"

    def test_period_length(self):
        ins = PaperInsights(numeric_results=[
            _r("y", 94, "years", metric="years", period_start=1926, period_end=2023, excluded_years=[1, 2, 3, 4]),
            _r("y2", 17, "years", metric="years", period_start=1964, period_end=1981),
        ])
        assert [c.status for c in checks.check_period_lengths(ins)] == ["pass", "fail"]

    def test_example_paper_inconsistencies_found(self, example_insights):
        comp = checks.check_compounding(example_insights)
        bad = [c for c in comp if c.status == "fail"]
        # Exhibit 3: 1982-2023 small 11.50% cannot be built from 12.8/10.0/7.8 (=10.87%)
        assert any("1982-2023" in c.message and "Small" in c.message for c in bad)
        # 1926-1963 is consistent with its two six-period halves
        ok = [c for c in comp if c.status == "pass" and "1926-1963" in c.message]
        assert len(ok) == 2
        assert all(c.status == "pass" for c in checks.check_derivations(example_insights))
        assert all(c.status == "pass" for c in checks.check_period_lengths(example_insights))


# ---------------------------------------------------------------------------
# citations
# ---------------------------------------------------------------------------

PAPER_TEXT = """Size effects (Banz 1981; Fama and French 1992) are robust (Shumway 1994).
Blitz, Baltussen and van Vliet (2020) agree. Jensen et al. (2023) find no crisis.

REFERENCES
Banz, RW, 1981. The relationship between return and market value. Journal of Financial Economics.
Blitz, D., Baltussen, G., & van Vliet, P. (2020). When Equity Factors Drop Their Shorts.
Fama, E.F. and French, K.R., 1992. The cross-section of expected stock returns. The Journal of
Finance, 47(2), pp.427-465.
Harvey, C. R., Liu, Y. and Zhu, H., 2016. and the cross-section.
Jensen, T.I., Kelly, B. and Pedersen, L.H., 2023. Is there a replication crisis in finance?
Shumway, Tyler, 1997, The delisting bias in CRSP data. Journal of Finance 52, 327-340.
"""


def test_citations():
    refs = checks.parse_references(PAPER_TEXT)
    assert [r[0] for r in refs] == ["Banz", "Blitz", "Fama", "Harvey", "Jensen", "Shumway"]
    results, flags = checks.check_citations(PAPER_TEXT)
    msgs = " ".join(c.message for c in results)
    assert "Shumway" in msgs and "1997" in msgs
    assert "Harvey 2016" in msgs  # never cited
    assert "Blitz" not in [f.message.split("'")[1].split()[0] for f in flags if "'" in f.message]
    assert [f.code for f in flags] == ["CITATION_MISMATCH"]


def test_methodology_flags_and_scores(example_insights):
    codes = {f.code for f in checks.methodology_flags(example_insights)}
    assert {"NO_SIGNIFICANCE_TESTS", "NO_OUT_OF_SAMPLE", "PROPRIETARY_DATA"} <= codes
    rep = checks.assess(example_insights, PAPER_TEXT)
    assert 0 <= rep.overall_score <= 100
    assert rep.internal_consistency_score < 100


# ---------------------------------------------------------------------------
# extraction
# ---------------------------------------------------------------------------


def _paper() -> PaperText:
    return PaperText(pages=[
        "Do Factors Work?\nA Study\n\nAbstract\nWe study size from 1926 – 2023 using the Kenneth French data library "
        "and CRSP. Small stocks beat large by 161 basis points.\nKey takeaways\n"
        "• Small stocks outperform on average over the full sample period.\n"
        "• Long-only portfolios lag for decades at a time, free of transaction costs.\n",
        "Exhibit 1\nGrowth of a Dollar\nExhibit 1 shows the growth.\n" + PAPER_TEXT,
    ], source="ssrn-5098799.pdf")


def test_heuristic_extract():
    ins = heuristic_extract(_paper())
    assert ins.metadata.title.startswith("Do Factors Work?")
    assert ins.metadata.identifier == "SSRN 5098799"
    assert len(ins.key_takeaways) == 2
    assert [e.title for e in ins.exhibits] == ["Growth of a Dollar"]
    names = {d.name for d in ins.datasets}
    assert {"Kenneth French Data Library", "CRSP"} <= names
    assert ins.methodology.sample_period.startswith("1926")
    assert ins.methodology.transaction_costs_modeled is False
    assert any(r.value == 161 and r.unit == "bp" for r in ins.numeric_results)


class FakeLLM:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def complete(self, messages, system="", max_tokens=4096):
        self.calls.append(messages)
        from app.core.llm import LLMResponse
        return LLMResponse(content=self.replies.pop(0), tool_calls=[], prompt_tokens=1, completion_tokens=1,
                           latency_ms=1, model="fake", provider="fake")


def test_llm_extract_with_repair(example_insights):
    good = example_insights.model_dump_json()
    llm = FakeLLM(['{"numeric_results": [{"id": 1}]}', f"```json\n{good}\n```"])
    ins = llm_extract(_paper(), llm=llm)
    assert ins.extraction_method == "llm"
    assert len(llm.calls) == 2 and "did not validate" in llm.calls[1][-1]["content"]
    assert all(f.source == "llm" for f in ins.red_flags)


def test_parse_json_object():
    assert _parse_json_object('Here:\n```json\n{"a": 1}\n```') == {"a": 1}


# ---------------------------------------------------------------------------
# replication: French parser, analytics, recipe end-to-end on synthetic data
# ---------------------------------------------------------------------------

FRENCH_CSV = """This file was created using the 202312 CRSP database.
The 1-month TBill rate data until 202405 are from Ibbotson Associates.

,Mkt-RF,SMB,HML,RF
192607,   2.89,  -2.55,  -2.39,   0.22
192608,   2.64,  -1.14,   3.81,   0.25

 Annual Factors: January-December
,Mkt-RF,SMB,HML,RF
1927,  29.47,  -2.04,  -3.54,   3.12

Copyright 2024 Kenneth R. French
"""


def test_parse_french_csv():
    blocks = french.parse_french_csv(FRENCH_CSV)
    m = french.find_block(blocks, monthly=True)
    assert list(m.columns) == ["Mkt-RF", "SMB", "HML", "RF"]
    assert m.loc[pd.Period("1926-07", "M"), "Mkt-RF"] == pytest.approx(0.0289)
    a = french.find_block(blocks, "Annual", monthly=False)
    assert a.loc[1927, "RF"] == pytest.approx(0.0312)


def test_fetch_raw_from_data_dir(tmp_path):
    (tmp_path / "F-F_Research_Data_Factors.csv").write_text(FRENCH_CSV)
    df = french.market_and_factors(data_dir=tmp_path, offline=True)
    assert df["MKT"].iloc[0] == pytest.approx(0.0289 + 0.0022)
    with pytest.raises(FileNotFoundError):
        french.fetch_raw("nope", data_dir=tmp_path, cache_dir=tmp_path / "c", offline=True)


def test_analytics_basic():
    idx = pd.period_range("2000-01", "2001-12", freq="M")
    r = pd.Series(0.01, index=idx)
    assert A.annualize(r) == pytest.approx(1.01 ** 12 - 1)
    ann = A.calendar_year_returns(r)
    assert list(ann.index) == [2000, 2001]
    assert A.period_annualized(ann, 2000, 2001) == pytest.approx(1.01 ** 12 - 1)
    assert A.period_annualized(ann, 2000, 2001, exclude=[2001]) == pytest.approx(1.01 ** 12 - 1)
    assert A.longest_run([True, True, False, True]) == 2
    assert A.rolling_excess(r * 2, r, 12).iloc[-1] > 0


def _synthetic_data(seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.period_range("1926-07", "2023-12", freq="M")
    n = len(idx)
    mkt = pd.Series(rng.normal(0.008, 0.045, n), index=idx)
    smb = pd.Series(rng.normal(0.002, 0.03, n), index=idx)
    small = mkt + smb + rng.normal(0, 0.01, n)
    return {"MKT": mkt, "SMB": smb, "HML": smb * 0, "RF": mkt * 0, "SMALL": small,
            "BIG_LoBM": mkt + rng.normal(-0.0005, 0.015, n), "BIG_HiBM": mkt + rng.normal(0.001, 0.02, n)}


def test_recipe_end_to_end(example_insights, tmp_path):
    res = factor_fluctuation.run(insights=example_insights, data=_synthetic_data(), n_sims=200)
    t = res.tables["exhibit3_subperiods"]
    assert len(t) == 10 and {"small_paper", "small_repl", "spread_repl_bp"} <= set(t.columns)
    assert t.loc[t.period == "1926-2023", "small_paper"].iloc[0] == 11.83
    names = {c.check for c in res.checks}
    assert {"ex3_spread", "ex3_extreme_years", "ex4_min", "claim_C7_large_value_1963_1990",
            "claim_C8_random_fluctuation"} <= names
    assert all(c.status in ("pass", "warn", "fail", "skip") for c in res.checks)

    out = analyze(None, insights=example_insights, recipe="factor-fluctuation",
                  recipe_kwargs={"data": _synthetic_data(), "n_sims": 200})
    paths = save(out, tmp_path)
    assert (tmp_path / "replication" / "exhibit3_subperiods.csv").exists()
    md = paths["report"].read_text()
    assert "## Replication output" in md and "Replication vs. public data" in md
    json.loads(paths["legitimacy"].read_text())


def test_suggest_recipes(example_insights):
    assert suggest_recipes(example_insights) == ["factor-fluctuation"]
    assert suggest_recipes(PaperInsights()) == []


def test_papers_route(example_insights):
    pytest.importorskip("multipart")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.routes import papers

    app = FastAPI()
    app.include_router(papers.router, prefix="/api/v1")
    client = TestClient(app)
    assert "factor-fluctuation" in client.get("/api/v1/papers/recipes").json()
    body = "\f".join(_paper().pages).encode()
    r = client.post("/api/v1/papers/analyze", files={"file": ("paper.txt", body, "text/plain")},
                    data={"use_llm": "false"})
    assert r.status_code == 200
    data = r.json()
    assert data["insights"]["extraction_method"] == "heuristic"
    assert "Scorecard" in data["report_markdown"]
