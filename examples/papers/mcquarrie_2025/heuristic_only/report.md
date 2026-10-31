# Paper Lab report: Do Factor Strategies Beat the Market? Sometimes Yes. Sometimes No.

*Unknown authors* · 2024 ·  · SSRN 5098799 · extraction: **heuristic**

## Scorecard

| Overall | Rigor | Internal consistency | Replicability |
|---|---|---|---|
| **59/100** | 47 | 97 | 30 |

**Verdict:** Weak: material methodological gaps or inconsistencies; do not trade without independent replication.

Automated checks: 0 pass · 3 warn · 0 fail · 0 skipped

## Summary

**Thesis.** Recent academic work has restored factors to their original luster. State-of-the-art statistical analyses using global data have validated dozens of factors in addition to the size and value factors initially proposed by Fama and French. Concerns that factor outperformance had been arbitraged away after publication have been put to rest.

Following two decades of skepticism and doubt, combined with worries about a replication crisis in finance, factors such as size and value have re-emerged as statistically robust effects, verified by multiple author teams using larger and more comprehensive datasets than heretofore available. Historical evidence simultaneously shows that even well-attested factors, when implemented as long-only portfolios in the world, have repeatedly underperformed the market for periods lasting a decade or more. This paper counterposes the historical and statistical evidence and suggests an integration.

**Key takeaways (as stated by the authors)**

- Recent academic work has restored factors to their original luster. State-of-the-art statistical analyses using global data have validated dozens of factors in addition to the size and value factors initially proposed by Fama and French. Concerns that factor outperformance had been arbitraged away after publication have been put to rest.
- Academic work uses long-short factors free of transaction costs and margin interest. Most investors who pursue factor strategies in the world are limited to long-only portfolios that do incur transaction costs. The historical record shows recurring periods of sustained factor under-performance for such long-only portfolios.
- The paper reconciles the statistical evidence with investor experience to sound a cautionary note for portfolio managers. A positive monthly mean obtained over many decades, using long-short portfolios, is quite compatible with periods of lagging performance by long-only portfolios that can persist for arbitrarily long periods.

## Methodology spec (for rebuilding the model)

- **Sample:** 1926-2024 (99 yrs)
- **Frequency:** monthly
- **Long-short:** yes
- **Transaction costs modeled:** no
- **Fees included:** yes
- **Statistical tests:** Fama-MacBeth regression, CAPM / factor regression
- **Significance reported:** not stated
- **Out-of-sample test:** not stated
- **Robustness checks:** none
- **Strategies tested:** not stated
- **Survivorship bias addressed:** not stated
- **Look-ahead bias addressed:** not stated

## Data

| dataset | public | period | access / substitute |
|---|---|---|---|
| Kenneth French Data Library | yes |  | https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html |
| CRSP | no |  | proprietary. Substitute: Kenneth French portfolios (built from CRSP) or yfinance |
| Ibbotson SBBI Yearbook | no |  | proprietary. Substitute: Kenneth French size portfolios (bottom quintile/decile) for small stocks; French market return for large stocks |
| Mutual fund total returns | yes |  | Adjusted closes from Yahoo Finance (e.g. VFINX, VTSMX, DFSCX, DFLVX) |
| UBS Global Investment Returns Yearbook | no |  | proprietary. Substitute: none identified |

## Exhibits

| exhibit | p. | shows | replicable | notes |
|---|---|---|---|---|
| Exhibit 1: Fluctuating Performance of Small Stocks | 4 |  | not stated |  |
| Exhibit 2: Fluctuating Performance of Value | 6 |  | not stated |  |
| Exhibit 3: Detail of Small Stock Fluctuations | 9 |  | not stated |  |
| Exhibit 4: Performance of Over-Sized, Over-Priced Stocks Relative to the Market | 13 |  | not stated |  |

## Red flags

- **[HIGH] NO_TRANSACTION_COSTS** (heuristic): Results are not shown net of transaction costs / bid-ask spreads (long-short factor returns).
- **[MEDIUM] LONG_SHORT_PAPER_RETURNS** (heuristic): Evidence relies on long-short paper portfolios; long-only implementation may differ materially.
- **[MEDIUM] NO_OUT_OF_SAMPLE** (heuristic): No explicit out-of-sample or hold-out validation.
- **[MEDIUM] NO_SIGNIFICANCE_TESTS** (heuristic): No t-statistics / p-values / confidence intervals reported for the headline differences.
- **[MEDIUM] PROPRIETARY_DATA** (heuristic): Uses proprietary data: UBS Global Investment Returns Yearbook. — No public substitute identified.
- **[LOW] CITATION_MISMATCH** (citations): In-text 'Shumway 1994)' but reference list has Shumway [1997]
- **[LOW] LOOKAHEAD_UNADDRESSED** (heuristic): Look-ahead / reporting-lag handling is not stated.
- **[LOW] NO_ROBUSTNESS** (heuristic): No robustness checks (alternative periods, definitions, weights) listed.
- **[LOW] PROPRIETARY_DATA** (heuristic): Uses proprietary data: CRSP. — Public substitute: Kenneth French portfolios (built from CRSP) or yfinance
- **[LOW] PROPRIETARY_DATA** (heuristic): Uses proprietary data: Ibbotson SBBI Yearbook. — Public substitute: Kenneth French size portfolios (bottom quintile/decile) for small stocks; French market return for large stocks
- **[LOW] SURVIVORSHIP_UNADDRESSED** (heuristic): Survivorship / delisting bias is not discussed.

## Automated checks

### Citations

- `WARN` **citations** — 24 references, 20 in-text citations, 1 inconsistencies
- `WARN` **citation_year** — In-text 'Shumway 1994)' but reference list has Shumway [1997]
- `WARN` **citation_uncited** — References never cited in text: Berk 2020, Davis 2000, Harvey 2016, Ibbotson 2020
