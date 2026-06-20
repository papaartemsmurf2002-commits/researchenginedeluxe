# Stage R106 Pre-May Adverse-Regime Resilience Selector Report

Date: 2026-06-12
Work packet: WPR106-163-pre-may-adverse-regime-resilience-selector
Status: rejected as candidate-ready, portfolio-ready, and promotion-ready evidence

## Scope

WPR106-163 tested whether the broad WPR106 artifact universe could be selected
by resilience to difficult pre-May regimes rather than by aggregate return,
component-pocket membership, or simple equal-sleeve construction.

All stress-month discovery, stress-day discovery, row scoring, portfolio
construction, ranking, and selection used only 2024-01-01 through 2026-04-30.
May 2026 was excluded from tuning and was used only after selected rows and
portfolios were fixed.

The packet is research-only and observe-only. It writes no candidate pack, no
paper/live artifact, no live configuration, no sizing change, no order path,
and no promotion claim.

## Inputs

The runner reused the WPR106-157 broad artifact normalizer to rebuild the local
artifact universe:

- Included packet directories: 43.
- Loaded metric rows: 2,925.
- Loaded pre-May trade rows: 591,571.
- Loaded May benchmark trade rows: 21,216.
- Behavior-deduplicated source rows: 1,915.

## Method

The selector discovered adverse pre-May months from cross-sectional monthly
source returns among active sources. The eight May-blind adverse months were:

- 2024-01
- 2024-06
- 2024-07
- 2024-09
- 2025-01
- 2025-09
- 2025-12
- 2026-04

It also discovered 80 adverse pre-May day clusters from daily cross-sectional
median and lower-quartile source returns, requiring broad active source
participation.

Rows were scored by total return, 2024-2025 search return, fixed 2026 Jan-Apr
validation return, annual losing-month counts, adverse-month return,
adverse-day return, drop-best-month robustness, best-month concentration,
drawdown, cost stress, active months, and active trade rate.

The packet selected fixed rows with packet, component, family, and symbol caps,
then generated small equal-sleeve portfolios from those rows using resilience
rank, packet/family diversity, low correlation, low same-day overlap,
adverse-complement, balanced, and rank-window constructions.

## Pre-May Results

Source-row resilience tiers across the 1,915-row deduped universe:

- Strict adverse-resilience rows: 84.
- Robust adverse-resilience rows: 101. This count includes rows that also meet
  strict conditions.
- Watch adverse-resilience rows: 1,083.

Fixed selected source rows:

- Selected rows: 100.
- Tier mix: 25 strict, 15 robust, 60 watch.
- Largest packet exposures: WPR106-135, WPR106-144, WPR106-139, and WPR106-119
  at 9 rows each.

Selected strict rows had a median pre-May total net return of +0.094694,
median 2026 Jan-Apr validation return of +0.009972, median adverse-month
return of +0.020207, median adverse-day return of +0.009851, median
drop-best-three-month return of +0.058869, and median two losing months.

Selected robust rows had stronger aggregate return but weaker day-cluster
resilience: median pre-May total net return was +0.301687, median validation
return was +0.042679, median adverse-month return was +0.055666, and median
adverse-day return was -0.002806.

Selected watch rows had high aggregate return but broad day-cluster weakness:
median pre-May total net return was +0.846649, median validation return was
+0.133034, median adverse-month return was +0.098381, and median adverse-day
return was -0.192813.

Portfolio construction generated 375 candidate portfolios, with 74 strict
pre-May portfolios and 100 robust pre-May portfolios. The fixed selected
portfolio set contained 38 portfolios: 20 strict, 4 robust, and 14 positive
fill rows.

## May 2026 Benchmark

May rejected the fixed selected source rows as a broad selector:

| Set | Rows | Positive | Negative | Flat | Best | Worst | Median | Mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Selected source rows | 100 | 30 | 68 | 2 | +0.065272 | -0.133646 | -0.006947 | -0.013354 |
| Selected portfolios | 38 | 3 | 35 | 0 | +0.011174 | -0.045880 | -0.009557 | -0.014304 |

Row-level tier detail:

| Tier | Rows | Positive | Negative | Flat | Median | Mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Strict | 25 | 8 | 16 | 1 | -0.000704 | -0.012046 |
| Robust | 15 | 7 | 8 | 0 | -0.007194 | -0.007756 |
| Watch | 60 | 15 | 44 | 1 | -0.014677 | -0.015298 |

Portfolio-level tier detail:

| Tier | Rows | Positive | Negative | Median | Mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| Strict | 20 | 2 | 18 | -0.004188 | -0.008147 |
| Robust | 4 | 1 | 3 | -0.002708 | +0.000522 |
| Positive fill | 14 | 0 | 14 | -0.026459 | -0.027335 |

The best May portfolio was a 2-sleeve low-correlation portfolio combining a
WPR106-132 trend-state row and a WPR106-139 calendar row, at +0.011174. It is
not candidate-ready because the selected portfolio family fails as a broad
May holdout and the supporting source family remains mixed.

## Pockets And Rejections

Positive May pockets that remain research-only:

- WPR106-146 cross-symbol relative-strength trade-veto rows: 4/4 positive,
  median +0.031309, best +0.047219.
- WPR106-128 anchored VWAP flow-impulse rows: 4/4 positive, median +0.006251.
- Small one-row positives appeared in WPR106-132, WPR106-134, WPR106-153,
  WPR106-120, and WPR106-131, but each is too narrow to stand alone.

Negative or still-suspect areas:

- WPR106-139 calendar/session exposure remains strongly May-negative in this
  selector: 0/9 positive, median -0.020699, mean -0.036181.
- WPR106-136 cross-family KNN trade-veto rows remain negative: 0/4 positive,
  with each selected row at -0.070820.
- WPR106-156 recent complement portfolios remain negative: 0/7 positive.
- WPR106-113 remains negative: 0/5 positive.

## Decision

WPR106-163 rejects the pre-May adverse-regime resilience selector as
candidate-ready, portfolio-ready, or promotion-ready evidence. The selector
improved the May-positive row count relative to several previous broad
selectors, but the fixed May benchmark still has a negative median and mean,
and the fixed portfolios remain mostly negative.

The most consistent research-only follow-up clues remain WPR106-146
cross-symbol relative-strength trade-veto and WPR106-128 anchored VWAP
flow-impulse rows. Any future follow-up must define its source universe,
controls, and pre-May selection criteria without using May 2026 as a tuning
signal.

## Artifacts

- Runner:
  `data/research/wpr106_163_pre_may_adverse_regime_resilience_selector/scripts/run_wpr106_163_pre_may_adverse_regime_resilience_selector.py`
- Summary:
  `data/research/wpr106_163_pre_may_adverse_regime_resilience_selector/wpr106_163_pre_may_adverse_regime_resilience_selector_summary.json`
- Source ranking:
  `data/research/wpr106_163_pre_may_adverse_regime_resilience_selector/pre_may/adverse_resilience_source_ranking.parquet`
- Selected source rows:
  `data/research/wpr106_163_pre_may_adverse_regime_resilience_selector/pre_may/selected_pre_may_adverse_resilience_rows.parquet`
- May source benchmark:
  `data/research/wpr106_163_pre_may_adverse_regime_resilience_selector/may_benchmark/selected_may_adverse_resilience_metrics.parquet`
- Selected portfolio ranking:
  `data/research/wpr106_163_pre_may_adverse_regime_resilience_selector/pre_may/selected_pre_may_adverse_resilience_portfolios.parquet`
- May portfolio benchmark:
  `data/research/wpr106_163_pre_may_adverse_regime_resilience_selector/may_benchmark/selected_may_adverse_resilience_portfolio_metrics.parquet`

## Validation

Passed:

- `python -m compileall -q data/research/wpr106_163_pre_may_adverse_regime_resilience_selector/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

Contract result: 460 passed.
