# Stage R106 KNN Complement Coverage Ensemble Search Report

Date: 2026-06-11
Packet: WPR106-122
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of all source deduplication, member choice, weighting
choice, replay-policy choice, ranking, and selection. Because no strict or
loose pre-May combo existed, May was not benchmarked for selected combos.

## Method

The runner
`data/research/wpr106_122_knn_complement_coverage_ensemble_search/scripts/run_wpr106_122_knn_complement_coverage_ensemble_search.py`
tests whether WPR106-117 annual-target Lorentzian/KNN neighborhoods can be
combined into active, month-stable portfolios. The economic hypothesis was
simple: WPR106-117 rows had acceptable annual losing-month counts but too few
active months, so complementary KNN neighborhoods might add activity without
breaking stability.

Inputs:

- `data/research/wpr106_117_knn_annual_target_coverage_expansion/pre_may/selected_pre_may.csv`
- `data/research/wpr106_117_knn_annual_target_coverage_expansion/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_117_knn_annual_target_coverage_expansion/may_benchmark/selected_may_benchmark_trades.parquet`

The first implementation attempted to replay a broader WPR106-117 source pool
from ranking rows. That broader source-replay pass timed out before writing
final evidence. The final closed run narrowed to the already fixed WPR106-117
selected KNN rows and deduplicated those rows by actual pre-May trade and
monthly-return fingerprints.

Final fixed grid:

- Deduped source behaviors: 5.
- Source pre-May trades: 420.
- Portfolio member counts: 2, 3, 4, and 5.
- Weight policies: equal, inverse drawdown, active-month balance, and
  return-tempered.
- Max trades per day: 1, 2, and 4.
- Concurrent caps: 1, 2, and 3.
- Same-symbol overlap blocking: enabled.
- Portfolio-level day caps and concurrent caps: enabled.
- Cost-stress recomputation: 1.00x, 1.25x, 1.50x, and 2.00x round-trip cost.

## Source Pool

The 27 WPR106-117 selected rows collapsed to 5 unique pre-May source behaviors:

- ETHUSDT trend-pullback-state long, Asia/all, 86 trades, 18 active months,
  5 losing months, +0.304182 pre-May.
- ETHUSDT price-path-vol short, US/trend, 69 trades, 18 active months,
  4 losing months, +0.180604 pre-May.
- ETHUSDT price-path-vol short, US/trend, 70 trades, 18 active months,
  4 losing months, +0.169168 pre-May.
- BTCUSDT trend-pullback-state long, all/high-vol, 105 trades, 17 active
  months, 5 losing months, +0.227545 pre-May.
- BTCUSDT trend-pullback-state long, all/high-vol, 90 trades, 17 active
  months, 5 losing months, +0.223524 pre-May.

The deduplication result is itself useful: the apparently larger WPR106-117
selected set had only five distinct source trade behaviors.

## Pre-May Results

Full grid:

- Candidate rows: 936.
- Positive pre-May rows: 936.
- Annual-target pre-May rows: 72.
- Combo-loose rows: 0.
- Combo-strict rows: 0.
- Selected diagnostic rows: 24.

Diagnostic split:

- `annual_target_sparse`: 8 selected rows, 17 active months, 5 losing months,
  +0.103165 to +0.111762 pre-May, max drawdown -0.044936 to -0.048680.
- `active_coverage_annual_fail`: 16 selected rows, 26 active months, 7 to 8
  losing months, +0.134198 to +0.233549 pre-May, max drawdown -0.037513 to
  -0.063984.

The tradeoff was consistent across the grid:

- Annual-target combos never exceeded 18 active months.
- Higher-coverage combos reached 23 to 26 active months, but failed the annual
  target, typically with 4 losing months in 2024 and 2 to 4 losing months in
  2025.
- The best active-coverage diagnostic row used 3 behaviors, 2 symbols,
  active-month-balanced weights, 260 trades, 26 active months, 7 losing months,
  +0.233549 pre-May, max drawdown -0.063984, and best-month share 0.195212.

## May Benchmark

May was not benchmarked because no selected row passed the strict or loose
pre-May combo gates. The runner wrote empty May benchmark tables and records:

- May 2026 benchmark-only: true.
- May 2026 used for selection: false.
- Selected May positive: 0.
- Selected May negative: 0.
- Selected May flat: 0.

## Decision

This packet rejects KNN complement coverage ensembles as candidate-ready
evidence. Combining the WPR106-117 KNN rows solved one problem only by creating
another: rows that preserved annual month stability remained too sparse, and
rows that became active enough failed the annual losing-month standard.

The result narrows the KNN direction. The WPR106-117 rows are not merely missing
a simple portfolio-combination layer. Further KNN work should require genuinely
new source behavior, such as different feature construction, neighbor labels,
temporal spacing, or filters that add active months without adding the 2024 and
2025 losing-month clusters observed here.

## Validation

Passed:

```powershell
python -m compileall -q data/research/wpr106_122_knn_complement_coverage_ensemble_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
