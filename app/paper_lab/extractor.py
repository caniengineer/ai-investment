"""Turn paper text into ``PaperInsights``.

Two extractors:

* ``llm_extract``       - asks the configured LLM (Claude / OpenAI via app.core.llm) for
                          the full structured spec. Best quality; needs an API key.
* ``heuristic_extract`` - regex/keyword based, offline, no API key. Gets metadata,
                          abstract, takeaways, exhibits, datasets, sample period and
                          methodology hints. Good enough to triage a paper and to feed
                          the citation / red-flag checks.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from app.paper_lab.pdf_text import PaperText
from app.paper_lab.schema import (
    Dataset,
    Exhibit,
    Methodology,
    NumericResult,
    PaperInsights,
    PaperMetadata,
)

logger = logging.getLogger("alphaagent.paper_lab.extractor")

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "paper_extract.txt"
MAX_CHARS = 180_000

# ---------------------------------------------------------------------------
# Known data sources: keyword -> Dataset template
# ---------------------------------------------------------------------------

KNOWN_DATASETS: list[tuple[str, Dataset]] = [
    (r"Kenneth French|French(?:'s)? data library|Fama[- ]French (?:data|factors|portfolios)",
     Dataset(name="Kenneth French Data Library", provider="Dartmouth / K. French",
             description="Fama-French factors and sorted portfolios, monthly from 1926",
             public=True, url="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html")),
    (r"\bCRSP\b", Dataset(name="CRSP", provider="Center for Research in Security Prices",
                          description="US stock returns", public=False,
                          substitute="Kenneth French portfolios (built from CRSP) or yfinance")),
    (r"\bCompustat\b", Dataset(name="Compustat", provider="S&P Global", public=False,
                               substitute="SEC EDGAR XBRL financial statements")),
    (r"\bSBBI\b|Ibbotson|Stocks, Bonds, Bills", Dataset(
        name="Ibbotson SBBI Yearbook", provider="Morningstar / Ibbotson", public=False,
        description="Annual US asset class returns from 1926",
        substitute="Kenneth French size portfolios (bottom quintile/decile) for small stocks; "
                   "French market return for large stocks")),
    (r"\bI/B/E/S\b|\bIBES\b", Dataset(name="I/B/E/S", provider="LSEG", public=False)),
    (r"\bTAQ\b", Dataset(name="TAQ", provider="NYSE", public=False)),
    (r"Datastream", Dataset(name="Datastream", provider="LSEG", public=False)),
    (r"Bloomberg", Dataset(name="Bloomberg", provider="Bloomberg LP", public=False)),
    (r"\bMSCI\b", Dataset(name="MSCI indexes", provider="MSCI", public=False)),
    (r"\bFRED\b", Dataset(name="FRED", provider="St. Louis Fed", public=True, url="https://fred.stlouisfed.org")),
    (r"Yahoo|yfinance", Dataset(name="Yahoo Finance", provider="Yahoo", public=True)),
    (r"Vanguard|DFA |Dimensional Fund|mutual fund", Dataset(
        name="Mutual fund total returns", provider="Fund companies / Yahoo Finance",
        description="Fund NAV total returns (net of fees)", public=True,
        access_notes="Adjusted closes from Yahoo Finance (e.g. VFINX, VTSMX, DFSCX, DFLVX)")),
    (r"Global Investment Returns Yearbook|Dimson,? Marsh", Dataset(
        name="UBS Global Investment Returns Yearbook", provider="UBS / Dimson-Marsh-Staunton",
        public=False)),
]

MONTHS = {"January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"}

_RANGE_RE = re.compile(r"\b(1[89]\d{2}|20\d{2})\s*(?:-|–|—|to|through)\s*(1[89]\d{2}|20\d{2}|present)\b")
_NUM_RE = re.compile(
    r"(?P<num>[-−]?\$?\d[\d,]*(?:\.\d+)?)\s*(?P<unit>%|percent|basis points|bp\b|X\b|times\b)", re.I
)


def _sentences(text: str) -> list[str]:
    flat = re.sub(r"\s+", " ", text)
    return re.split(r"(?<=[.!?])\s+(?=[A-Z])", flat)


def _section(text: str, start_pat: str, end_pats: list[str], max_len: int = 3000) -> str:
    m = re.search(start_pat, text, re.I)
    if not m:
        return ""
    rest = text[m.end():]
    end = len(rest)
    for pat in end_pats:  # case-sensitive: end markers are often ALL-CAPS headings
        e = re.search(pat, rest)
        if e and e.start() < end:
            end = e.start()
    return rest[: min(end, max_len)].strip()


def heuristic_extract(paper: PaperText) -> PaperInsights:
    text = paper.plain_text
    flat = re.sub(r"[ \t]+", " ", text)
    lower = flat.lower()

    # --- metadata -----------------------------------------------------------
    first_lines = [ln.strip() for ln in paper.pages[0].splitlines() if ln.strip()] if paper.pages else []
    title = " ".join(first_lines[:2]) if first_lines else ""
    years = [int(y) for y in re.findall(r"\b(19[5-9]\d|20[0-4]\d)\b", flat)]
    meta = PaperMetadata(title=title, pages=len(paper.pages), year=max(years) if years else None)
    ssrn = re.search(r"ssrn[-_ ]?(\d{6,8})", paper.source, re.I)
    if ssrn:
        meta.identifier = f"SSRN {ssrn.group(1)}"

    # --- abstract & takeaways ----------------------------------------------
    abstract = _section(flat, r"\bAbstract\b", [r"Key [Tt]akeaways", r"\n\s*(?:1\.?\s*)?(?:Introduction|INTRODUCTION)", r"Keywords", r"JEL"])
    takeaways_block = _section(flat, r"Key takeaways", [r"\n[A-Z][A-Z ]{6,}\n", r"“", r"\"The test"], 4000)
    takeaways = [re.sub(r"\s+", " ", t).strip() for t in re.split(r"\s*[•●▪]\s*", takeaways_block) if len(t.strip()) > 30]

    # --- exhibits ------------------------------------------------------------
    exhibits: dict[str, Exhibit] = {}
    for pi, page in enumerate(paper.pages):
        for m in re.finditer(r"^\s*(Exhibit|Table|Figure)\s+(\d+)\s*[:.]?\s*(.*)$", page, re.M):
            ex_id = f"{m.group(1)} {m.group(2)}"
            title_line = m.group(3).strip()
            if title_line[:1].islower():  # prose mentioning the exhibit, not its caption
                continue
            if not title_line:
                nxt = page[m.end():].strip().splitlines()
                title_line = nxt[0].strip() if nxt else ""
            if ex_id not in exhibits or (not exhibits[ex_id].title and title_line):
                exhibits[ex_id] = Exhibit(id=ex_id, title=title_line[:120], page=pi + 1,
                                          kind="table" if m.group(1) == "Table" else "figure")

    # --- datasets --------------------------------------------------------------
    datasets = []
    for pat, ds in KNOWN_DATASETS:
        if re.search(pat, flat):
            datasets.append(ds.model_copy())

    # --- sample period -----------------------------------------------------------
    ranges = []
    for a, b in _RANGE_RE.findall(flat):
        end = max(years) if b == "present" and years else int(b) if b != "present" else None
        if end and int(a) <= end:
            ranges.append((int(a), end))
    sample_period, sample_years = "", None
    if ranges:
        lo, hi = min(r[0] for r in ranges), max(r[1] for r in ranges)
        sample_period, sample_years = f"{lo}-{hi}", hi - lo + 1

    def has(*pats: str) -> bool:
        return any(re.search(p, lower) for p in pats)

    def tri(*pats: str) -> Optional[bool]:
        return True if has(*pats) else None

    tests = [name for name, pat in [
        ("Fama-MacBeth regression", r"fama[- ]macbeth"), ("t-statistics", r"\bt-stat|\bt stat"),
        ("p-values", r"p-value|p < 0"), ("bootstrap", r"bootstrap"), ("GRS test", r"\bgrs\b"),
        ("Newey-West", r"newey"), ("Sharpe ratio", r"sharpe"), ("CAPM / factor regression", r"\bcapm\b|\balpha\b"),
    ] if has(pat)]
    methodology = Methodology(
        sample_period=sample_period,
        sample_years=sample_years,
        frequency="monthly" if has(r"\bmonthly\b") else ("annual" if has(r"\bannual") else ""),
        long_short=True if has(r"long-short|long/short|\bsmb\b|\bhml\b") else None,
        transaction_costs_modeled=(False if has(r"free of transaction costs", r"without transaction costs",
                                                r"ignor\w+ transaction costs") else tri(r"transaction cost", r"trading cost")),
        fees_included=tri(r"net of fees", r"expense ratio", r"mutual fund"),
        statistical_tests=tests,
        significance_reported=True if has(r"\bt-stat", r"p-value", r"standard error", r"significant at") else None,
        out_of_sample_test=tri(r"out-of-sample", r"out of sample", r"holdout"),
        survivorship_bias_addressed=tri(r"survivorship"),
        lookahead_bias_addressed=tri(r"look-ahead", r"lookahead", r"point-in-time"),
        multiple_testing_adjustment=tri(r"multiple testing", r"bonferroni", r"false discovery", r"data[- ]snooping"),
    )

    # --- quantitative mentions in text -----------------------------------------
    numeric: list[NumericResult] = []
    for sent in _sentences(text):
        if len(numeric) >= 80:
            break
        for m in _NUM_RE.finditer(sent):
            raw_num = m.group("num").replace("−", "-").replace("$", "").replace(",", "")
            try:
                val = float(raw_num)
            except ValueError:
                continue
            u = m.group("unit").lower()
            unit = "percent" if u in ("%", "percent") else "bp" if u in ("basis points", "bp") else "multiple"
            rng = _RANGE_RE.search(sent)
            numeric.append(NumericResult(
                id=f"txt_{len(numeric) + 1}", series="(text mention)", metric="text_mention",
                value=val, unit=unit, comparator="approx",
                period_start=int(rng.group(1)) if rng else None,
                period_end=int(rng.group(2)) if rng and rng.group(2).isdigit() else None,
                source="text", quote=sent[:300]))

    summary = re.sub(r"\s+", " ", abstract)[:1500]
    return PaperInsights(
        metadata=meta,
        summary=summary,
        thesis=takeaways[0] if takeaways else (summary.split(". ")[0] if summary else ""),
        key_takeaways=takeaways,
        exhibits=list(exhibits.values()),
        datasets=datasets,
        methodology=methodology,
        numeric_results=numeric,
        extraction_method="heuristic",
    )


# ---------------------------------------------------------------------------
# LLM extraction
# ---------------------------------------------------------------------------


def _parse_json_object(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("LLM response contained no JSON object")
    return json.loads(raw[start: end + 1])


def llm_extract(paper: PaperText, llm=None, max_tokens: int = 16000) -> PaperInsights:
    """Ask the LLM for a full PaperInsights JSON. One repair round on validation errors."""
    if llm is None:
        from app.core.llm import get_llm_provider

        llm = get_llm_provider()

    schema = json.dumps(PaperInsights.model_json_schema(), separators=(",", ":"))
    system = PROMPT_PATH.read_text().replace("{schema}", schema)
    text = paper.full_text
    if len(text) > MAX_CHARS:
        logger.warning("Paper text truncated from %d to %d chars", len(text), MAX_CHARS)
        text = text[:MAX_CHARS]
    messages = [{"role": "user", "content": f"<paper source=\"{paper.source}\">\n{text}\n</paper>"}]

    last_err: Exception | None = None
    for attempt in range(2):
        resp = llm.complete(messages, system=system, max_tokens=max_tokens)
        try:
            insights = PaperInsights.model_validate(_parse_json_object(resp.content))
            insights.extraction_method = "llm"
            for f in insights.red_flags:
                f.source = "llm"
            return insights
        except (ValueError, ValidationError) as e:
            last_err = e
            logger.warning("LLM extraction attempt %d invalid: %s", attempt + 1, str(e)[:500])
            messages = messages + [
                {"role": "assistant", "content": resp.content},
                {"role": "user", "content": f"That JSON did not validate: {str(e)[:2000]}\n"
                                            "Return the corrected JSON object only."},
            ]
    raise RuntimeError(f"LLM extraction failed: {last_err}")


def extract(paper: PaperText, use_llm: bool = True, llm=None) -> PaperInsights:
    """LLM extraction when possible, heuristic otherwise. Heuristic fields fill LLM gaps."""
    heur = heuristic_extract(paper)
    if not use_llm:
        return heur
    try:
        ins = llm_extract(paper, llm=llm)
    except Exception as e:
        logger.warning("Falling back to heuristic extraction: %s", e)
        return heur
    if not ins.metadata.pages:
        ins.metadata.pages = heur.metadata.pages
    if not ins.exhibits:
        ins.exhibits = heur.exhibits
    if not ins.datasets:
        ins.datasets = heur.datasets
    return ins
