# Paper Lab report: Do Factor Strategies Beat the Market? Sometimes Yes. Sometimes No.

*Edward F. McQuarrie* · 2025 · SSRN working paper · SSRN 5098799 · extraction: **manual**

## Scorecard

| Overall | Rigor | Internal consistency | Replicability |
|---|---|---|---|
| **54/100** | 38 | 39 | 90 |

**Verdict:** Weak: material methodological gaps or inconsistencies; do not trade without independent replication.

Automated checks: 27 pass · 3 warn · 6 fail · 0 skipped

## Summary

**Thesis.** Factor premia are real on average but fluctuate: when you invest determines whether a long-only factor tilt beats the market.

Argues that statistically robust long-short factor premia (size, value) are compatible with long-only, with-cost factor portfolios lagging the market for a decade or more. Uses DFA fund histories (Exhibits 1-2), an SBBI/fund-based sub-period breakdown of small vs large stocks 1926-2023 with skewness probes (Exhibit 3) and trailing 10-year returns of big growth stocks vs the market from the French library (Exhibit 4).

**Key takeaways (as stated by the authors)**

- Recent academic work validates many factors with global data; arbitrage-away concerns are put to rest.
- Academic factors are long-short and cost-free; investors hold long-only portfolios with costs, which show recurrent decade-long underperformance.
- A positive long-run monthly mean is compatible with arbitrarily long periods of long-only underperformance.

## Claims

| id | kind | claim | evidence | how to test |
|---|---|---|---|---|
| C1 | main_thesis | A positive long-run monthly average premium on a long-short factor (SMB, HML) is compatible with long-only factor portfolios underperforming the market for a decade or more. | Exhibits 1-4 | Compute rolling 10-20y long-only factor-portfolio minus market annualized returns from French data; count windows < 0 while full-sample SMB/HML mean > 0. |
| C2 | empirical | All of the 1926-2023 small-stock excess return occurred in 1964-1981; 1926-1963 and 1982-2023 net to roughly zero (+7bp, -17bp). | Exhibit 3 | Annualized returns of small-cap portfolio vs large-cap index per sub-period. |
| C3 | empirical | Removing the 4 most extreme years (1933, 1943, 1945, 1967) eliminates the small-stock advantage (-8bp); removing WWII years cuts it from 161bp to 41bp. | Exhibit 3 skewness probes | Rank years by small minus large return, drop top 4, re-annualize the remaining 94 years. |
| C4 | empirical | DFA Microcap fund trailed the S&P 500 fund by ~2x in wealth 1982-1999 and doubled it 1999-2017; ending ~equal over 42 years. | Exhibit 1 | Total-return series of DFSCX vs VFINX from Yahoo Finance. |
| C5 | empirical | DFA Large Value beat Vanguard Total Market by 30% in wealth 1993-2007 and trailed by 30% 2007-2021. | Exhibit 2 | DFLVX vs VTSMX total returns. |
| C6 | empirical | Big low-B/M (growth) stocks - the anti-factor - outperformed the market over many trailing 10-year windows (1930s, 1990s, 2010s-2020s) and underperformed by up to ~4.5%/yr in windows ending in the early 1980s. | Exhibit 4 | French 6 portfolios ME/BM, BIG LoBM VW minus Mkt, trailing 120m annualized. |
| C7 | empirical | Large value outperformed the market in every 120-month roll ending within 1963-1990. | Text p.13 (no exhibit) | French BIG HiBM minus Mkt, trailing 120m, roll ends 1963-1990: all > 0. |
| C8 | interpretive | Periods of factor underperformance are best explained by random fluctuation of two volatile, imperfectly correlated series rather than arbitrage, macro variables or sector composition. | Argument, no formal test | Monte Carlo / block bootstrap of factor & market returns with the historical mean, vol and correlation; compare frequency/length of decade-long underperformance spells with history. |
| C9 | methodological | SMB (arithmetic, long-short) does not track the difference in annualized long-only returns; SMB is positive in most sub-periods regardless of sign of the long-only spread. | Exhibit 3 SMB column | Compare per-period SMB mean with geometric small-minus-market spread. |
| C10 | recommendation | Researchers should report when factors outperformed, dependence on shorting the anti-factor and on ignoring costs, and the skewness/volatility of outperformance. | Conclusion | (not testable) |

## Methodology spec (for rebuilding the model)

- **Research question:** Do long-only, with-cost factor portfolios beat the market over investor-relevant horizons, given robust long-short statistical evidence?
- **Universe:** US equities
- **Sample:** 1926-2023 (98 yrs)
- **Frequency:** annual (Exhibit 3), monthly (Exhibits 2, 4)
- **Portfolio construction:** Small: SBBI small stocks to 1981 then DFA Microcap fund; value: DFA Large Value fund; anti-factor: French 2x3 BIG/LoBM (above-median ME, bottom 30% B/M)
- **Weighting:** value-weighted (French portfolios); fund weighting
- **Rebalancing:** annual (French, end of June); fund-managed
- **Benchmark:** S&P 90/500 (SBBI) then Vanguard 500 fund; Vanguard Total Stock Market fund; French market return
- **Long-short:** no
- **Transaction costs modeled:** not stated
- **Fees included:** yes
- **Statistical tests:** none
- **Significance reported:** no
- **Out-of-sample test:** no
- **Robustness checks:** sub-period breakdowns (3 and 6 periods); drop 4 most extreme years; drop WWII years; wealth path reset at turning points
- **Strategies tested:** 3
- **Survivorship bias addressed:** not stated
- **Look-ahead bias addressed:** not stated
- **Formulas:**
  - `annualized return = (prod(1+r_t))^(1/years) - 1`
  - `Exhibit 4: trailing 120m annualized(BIG LoBM) - annualized(Mkt)`
  - `SMB = average monthly long-short spread (arithmetic)`
- **Notes:** Mixes index data (SBBI, gross of costs) with fund data (net of fees) in one series; start/end dates and 'reset' points are chosen ex post at turning points.

## Data

| dataset | public | period | access / substitute |
|---|---|---|---|
| Ibbotson SBBI Yearbook | no | 1926-1981 | proprietary. Substitute: French Portfolios_Formed_on_ME (Lo 20 / Lo 10 VW) for small; French market (Mkt-RF+RF) for large |
| Vanguard 500 Index (VFINX) and DFA US Micro Cap (DFSCX) | yes | 1982-2023 | Yahoo Finance adjusted close |
| DFA US Large Cap Value (DFLVX) and Vanguard Total Stock Market (VTSMX) | yes | 1993-06 to 2023-06 | Yahoo Finance adjusted close |
| Kenneth French Data Library: 6 Portfolios Formed on Size and B/M (2x3), F-F Research Factors | yes | 1926-2023 | https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html |

## Exhibits

| exhibit | p. | shows | replicable | notes |
|---|---|---|---|---|
| Exhibit 1: Fluctuating Performance of Small Stocks | 4 | Growth of $1 1981-2022, Vanguard S&P 500 fund vs DFA Microcap, with S&P line reset in 1999 | yes | Yahoo history for DFSCX may start later than 1981; French Lo 10 is a proxy. |
| Exhibit 2: Fluctuating Performance of Value | 6 | Growth of $1 6/1993-6/2023, Vanguard Total Market vs DFA Large Value, reset in 2007 | yes |  |
| Exhibit 3: Detail of Small Stock Fluctuations | 9 | Annualized small vs S&P returns and SMB for full period, 3 and 6 sub-periods, and two skewness probes | yes | SBBI proprietary: approximate with French size portfolios; expect level differences, signs should match. |
| Exhibit 4: Performance of Over-Sized, Over-Priced Stocks Relative to the Market | 12 | Trailing 120-month annualized return of BIG LoBM minus market, roll ends 1936-06 to 2023 | yes | Fully public data; exact replication expected. |

## Replication plan

1. Download F-F_Research_Data_Factors (monthly) and build market total return = Mkt-RF + RF.
2. Download Portfolios_Formed_on_ME, take value-weighted 'Lo 20' (NYSE bottom quintile ~ CRSP 9-10 / SBBI small) as small-stock proxy.
3. Compound to calendar-year returns; annualize (geometric) per Exhibit 3 period; SMB annual mean. → reproduces `ex3_*`
4. Drop the 4 years with the largest small-minus-market return (paper: 1933,1943,1945,1967) and WWII years; re-annualize. → reproduces `ex3_drop4_*, ex3_dropww2_*`
5. Download 6_Portfolios_2x3; trailing 120-month annualized BIG LoBM minus market; also BIG HiBM minus market for claim C7. → reproduces `ex4_min, ex4_max, C6, C7`
6. Fetch VFINX, DFSCX, VTSMX, DFLVX adjusted closes from Yahoo; rebuild growth-of-$1 and reset ratios. → reproduces `ex1_*, ex2_*`
7. Monte Carlo: simulate factor and market with historical mean/vol/correlation; distribution of longest underperformance spell, to test claim C8. → reproduces `C8`

## Red flags

- **[MEDIUM] ENDPOINT_SELECTION** (llm): Sub-period boundaries and wealth-reset points (1999, 2007) are chosen ex post at turning points, which maximizes the visual reversal. — Exhibits 1-2
- **[MEDIUM] INTERNAL_INCONSISTENCY** (consistency): Small Stocks 1926-2023 reported 11.83%; compounding sub-periods [three_period: 1926-1963:10.3%, 1964-1981:13.54%, 1982-2023:11.5%] gives 11.40% (arith 11.41%), gap +43 bp
- **[MEDIUM] INTERNAL_INCONSISTENCY** (consistency): Small Stocks 1926-2023 reported 11.83%; compounding sub-periods [six_period: 1926-1941:-1.2%, 1942-1963:19.5%, 1964-1981:13.5%, 1982-1999:12.8%, 2000-2017:10%, 2018-2023:7.8%] gives 11.13% (arith 11.33%), gap +70 bp
- **[MEDIUM] INTERNAL_INCONSISTENCY** (consistency): Small Stocks 1982-2023 reported 11.5%; compounding sub-periods [six_period: 1982-1999:12.8%, 2000-2017:10%, 2018-2023:7.8%] gives 10.87% (arith 10.89%), gap +63 bp
- **[MEDIUM] INTERNAL_INCONSISTENCY** (consistency): S&P 90/500 1926-2023 reported 10.22%; compounding sub-periods [three_period: 1926-1963:10.23%, 1964-1981:5.87%, 1982-2023:11.67%] gives 10.03% (arith 10.05%), gap +19 bp
- **[MEDIUM] INTERNAL_INCONSISTENCY** (consistency): S&P 90/500 1926-2023 reported 10.22%; compounding sub-periods [six_period: 1926-1941:3%, 1942-1963:15.8%, 1964-1981:5.9%, 1982-1999:17%, 2000-2017:5.4%, 2018-2023:12%] gives 9.83% (arith 9.97%), gap +39 bp
- **[MEDIUM] INTERNAL_INCONSISTENCY** (consistency): S&P 90/500 1982-2023 reported 11.67%; compounding sub-periods [six_period: 1982-1999:17%, 2000-2017:5.4%, 2018-2023:12%] gives 11.18% (arith 11.31%), gap +49 bp
- **[MEDIUM] NO_OUT_OF_SAMPLE** (heuristic): No explicit out-of-sample or hold-out validation.
- **[MEDIUM] NO_SIGNIFICANCE_TESTS** (heuristic): No t-statistics / p-values / confidence intervals reported for the headline differences.
- **[MEDIUM] NO_TRANSACTION_COSTS** (heuristic): Results are not shown net of transaction costs / bid-ask spreads.
- **[MEDIUM] RANDOMNESS_UNTESTED** (llm): The central 'random fluctuation' explanation is asserted, not tested (no simulation or bootstrap). — pp.11-12
- **[MEDIUM] SPLICED_SERIES** (llm): Exhibit 3 splices SBBI index data (gross, no costs) through 1981 with fund returns (net of fees) afterwards, so pre/post-1982 sub-periods are not like-for-like. — Exhibit 3 note
- **[LOW] CITATION_MISMATCH** (citations): In-text 'Shumway 1994)' but reference list has Shumway [1997]
- **[LOW] CLAIM_WITHOUT_EXHIBIT** (llm): 'Large value outperformed for every 120-month roll ending 1963-1990' is stated without an exhibit. — p.13
- **[LOW] LOOKAHEAD_UNADDRESSED** (heuristic): Look-ahead / reporting-lag handling is not stated.
- **[LOW] PROPRIETARY_DATA** (heuristic): Uses proprietary data: Ibbotson SBBI Yearbook. — Public substitute: French Portfolios_Formed_on_ME (Lo 20 / Lo 10 VW) for small; French market (Mkt-RF+RF) for large
- **[LOW] SMB_DEFINITION_UNCLEAR** (llm): How the SMB column is annualized (arithmetic monthly x12? compounded?) is not specified. — Exhibit 3
- **[LOW] SURVIVORSHIP_UNADDRESSED** (heuristic): Survivorship / delisting bias is not discussed.
- **[INFO] DESCRIPTIVE_ONLY** (heuristic): Evidence is descriptive (no formal statistical tests).

## Automated checks

### Internal consistency (numbers vs. each other)

- `FAIL` **compounding** — Small Stocks 1926-2023 reported 11.83%; compounding sub-periods [three_period: 1926-1963:10.3%, 1964-1981:13.54%, 1982-2023:11.5%] gives 11.40% (arith 11.41%), gap +43 bp
- `FAIL` **compounding** — Small Stocks 1926-2023 reported 11.83%; compounding sub-periods [six_period: 1926-1941:-1.2%, 1942-1963:19.5%, 1964-1981:13.5%, 1982-1999:12.8%, 2000-2017:10%, 2018-2023:7.8%] gives 11.13% (arith 11.33%), gap +70 bp
- `FAIL` **compounding** — Small Stocks 1982-2023 reported 11.5%; compounding sub-periods [six_period: 1982-1999:12.8%, 2000-2017:10%, 2018-2023:7.8%] gives 10.87% (arith 10.89%), gap +63 bp
- `FAIL` **compounding** — S&P 90/500 1926-2023 reported 10.22%; compounding sub-periods [three_period: 1926-1963:10.23%, 1964-1981:5.87%, 1982-2023:11.67%] gives 10.03% (arith 10.05%), gap +19 bp
- `FAIL` **compounding** — S&P 90/500 1926-2023 reported 10.22%; compounding sub-periods [six_period: 1926-1941:3%, 1942-1963:15.8%, 1964-1981:5.9%, 1982-1999:17%, 2000-2017:5.4%, 2018-2023:12%] gives 9.83% (arith 9.97%), gap +39 bp
- `FAIL` **compounding** — S&P 90/500 1982-2023 reported 11.67%; compounding sub-periods [six_period: 1982-1999:17%, 2000-2017:5.4%, 2018-2023:12%] gives 11.18% (arith 11.31%), gap +49 bp
- `PASS` **period_length** — ex3_all_1926_2023_years: 1926-2023 minus 0 excluded = 98 years, reported 98
- `PASS` **period_length** — ex3_three_period_1926_1963_years: 1926-1963 minus 0 excluded = 38 years, reported 38
- `PASS` **period_length** — ex3_three_period_1964_1981_years: 1964-1981 minus 0 excluded = 18 years, reported 18
- `PASS` **period_length** — ex3_three_period_1982_2023_years: 1982-2023 minus 0 excluded = 42 years, reported 42
- `PASS` **period_length** — ex3_six_period_1926_1941_years: 1926-1941 minus 0 excluded = 16 years, reported 16
- `PASS` **period_length** — ex3_six_period_1942_1963_years: 1942-1963 minus 0 excluded = 22 years, reported 22
- `PASS` **period_length** — ex3_six_period_1964_1981_years: 1964-1981 minus 0 excluded = 18 years, reported 18
- `PASS` **period_length** — ex3_six_period_1982_1999_years: 1982-1999 minus 0 excluded = 18 years, reported 18
- `PASS` **period_length** — ex3_six_period_2000_2017_years: 2000-2017 minus 0 excluded = 18 years, reported 18
- `PASS` **period_length** — ex3_six_period_2018_2023_years: 2018-2023 minus 0 excluded = 6 years, reported 6
- `PASS` **period_length** — ex3_drop4_years: 1926-2023 minus 4 excluded = 94 years, reported 94
- `PASS` **period_length** — ex3_dropww2_years: 1926-2023 minus 4 excluded = 94 years, reported 94
- `PASS` **derivation** — Small minus S&P (text): reported eq 161 bp; difference of ex3_all_1926_2023_small, ex3_all_1926_2023_sp gives 161
- `PASS` **derivation** — Small / S&P terminal wealth (text): reported gt 4 multiple; wealth_ratio of ex3_all_1926_2023_small, ex3_all_1926_2023_sp gives 4.142
- `PASS` **derivation** — Small minus S&P (text): reported eq 7 bp; difference of ex3_three_period_1926_1963_small, ex3_three_period_1926_1963_sp gives 7
- `PASS` **derivation** — Small minus S&P (text): reported eq -17 bp; difference of ex3_three_period_1982_2023_small, ex3_three_period_1982_2023_sp gives -17
- `PASS` **derivation** — Small minus S&P (text): reported approx -400 bp; difference of ex3_six_period_1926_1941_small, ex3_six_period_1926_1941_sp gives -420
- `PASS` **derivation** — Small minus S&P (text): reported approx 400 bp; difference of ex3_six_period_1942_1963_small, ex3_six_period_1942_1963_sp gives 370
- `PASS` **derivation** — Small minus S&P (text): reported approx 800 bp; difference of ex3_three_period_1964_1981_small, ex3_three_period_1964_1981_sp gives 767
- `PASS` **derivation** — Small minus S&P (text): reported eq -8 bp; difference of ex3_drop4_small, ex3_drop4_sp gives -8
- `PASS` **derivation** — Small minus S&P (text): reported eq 41 bp; difference of ex3_dropww2_small, ex3_dropww2_sp gives 41
- `PASS` **derivation** — S&P fund / DFA microcap wealth (text): reported approx 2 multiple; ratio of ex1_sp_1999, ex1_dfa_1999 gives 1.818
- `PASS` **derivation** — DFA microcap / S&P fund wealth (1999-2017) (text): reported approx 2 multiple; ratio of ex1_dfa_2017, ex1_sp_reset_2017 gives 2.164
- `PASS` **derivation** — DFA Large Value / Total Market wealth (1993-2007) (text): reported approx 1.3 multiple; ratio of ex2_dfa_2007, ex2_vtsm_2007 gives 1.312
- `PASS` **derivation** — DFA Large Value / Total Market wealth (2007-2021) (text): reported approx 0.7 multiple; ratio of ex2_dfa_reset_2021, ex2_vtsm_2021 gives 0.7001
- `PASS` **compounding** — Small Stocks 1926-1963 reported 10.3%; compounding sub-periods [six_period: 1926-1941:-1.2%, 1942-1963:19.5%] gives 10.30% (arith 10.78%), gap -0 bp
- `PASS` **compounding** — S&P 90/500 1926-1963 reported 10.23%; compounding sub-periods [six_period: 1926-1941:3%, 1942-1963:15.8%] gives 10.23% (arith 10.41%), gap +0 bp

### Citations

- `WARN` **citations** — 24 references, 20 in-text citations, 1 inconsistencies
- `WARN` **citation_year** — In-text 'Shumway 1994)' but reference list has Shumway [1997]
- `WARN` **citation_uncited** — References never cited in text: Berk 2020, Davis 2000, Harvey 2016, Ibbotson 2020

## Model / strategy ideas

- Size/value tilt timing: rolling 10y factor-minus-market spread as a regime indicator (test whether extreme negative spreads predict reversal).
- Long-only factor portfolio vs market with realistic costs and fees; estimate probability of 10y underperformance via block bootstrap.
- Anti-factor (big growth) momentum: does trailing 10y BIG LoBM outperformance persist or mean-revert?

## Open questions for replication

- Is the 1964-1981 small-stock surge robust to using CRSP deciles instead of SBBI?
- Do sub-period spreads survive with like-for-like (all index or all fund) data?
- What is the bootstrap probability of a 18y underperformance spell given SMB's mean and vol?
