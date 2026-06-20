# Stage R106 Monthly Dropout Stability Selector Report

Date: 2026-06-12
Packet: WPR106-159
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of dropout scoring, annual loss limits, rolling-window
diagnostics, exposure caps, ranking, and selection. May was replayed only after
the fixed pre-May selected rows were written.

## Method

The runner
`data/research/wpr106_159_monthly_dropout_stability_selector/scripts/run_wpr106_159_monthly_dropout_stability_selector.py`
reuses the WPR106-157 artifact-universe builder, which normalizes local WPR106
selected artifacts, behavior-de-duplicates accepted pre-May trade paths, and
recomputes common metrics from trade details.

Selection uses only 2024-01-01 through 2026-04-30:

- 2024, 2025, and 2026 Jan-Apr annual return and losing-month counts;
- total active, winning, losing, and flat/inactive month counts;
- best-month concentration and worst-month severity;
- returns after removing the best one, two, and three pre-May months;
- rolling three-month and six-month window counts and worst windows;
- early and late pre-May subperiod returns;
- packet, component, symbol, and behavior exposure caps.

The selector writes three pre-May tiers: `monthly_elite`,
`dropout_robust`, and `rolling_survivor`. The `monthly_elite` tier requires
positive return after removing the best three pre-May months, positive
six-month rolling windows, annual losing-month caps of 2/2/1 across
2024/2025/2026 Jan-Apr, cost-stress survival, drawdown control, and active
trade rates at or below five trades per active day.

Compute used vectorized pandas artifact loading and grouped metric replay from
the WPR106-157 builder. No CUDA path was used because this packet is an
artifact-level selector, not a new model/backtest grid, and no speedup was
claimed.

## Results

Broad source universe:

- Included packet directories: 43.
- Loaded metric rows: 2,925.
- Loaded pre-May trade rows: 591,571.
- Loaded May benchmark trade rows: 21,216.
- Behavior-deduplicated source rows: 1,915.
- Monthly-elite rows: 326.
- Dropout-robust rows: 442.
- Rolling-survivor rows: 849.

Selected pre-May set:

- Selected rows: 100.
- Selection tiers: 78 `monthly_elite`, 10 `dropout_robust`, and 12
  `rolling_survivor`.
- Largest packet exposures: 9 rows each from WPR106-144, WPR106-119,
  WPR106-137, WPR106-135, and WPR106-156.
- Trade-count range: 85 to 983.
- Active-month range: 21 to 28.
- Monthly losing-month range: 1 to 9.
- Pre-May total net-return range: +0.054780 to +2.480657.
- Drop-best-three pre-May return range: +0.035858 to +1.630755.
- Rolling six-month worst-window range: -0.046285 to +0.303412.
- Best single-month share range: 0.082205 to 0.321689.
- Best-three-positive-month share range: 0.224913 to 0.432183.
- Max-drawdown range: -0.395546 to -0.002712.

The top pre-May row is WPR106-139 `calendar-ad953bfdaa925347`, an ETHUSDT
calendar session momentum row with 488 trades, 4 losing active months,
+2.227919 pre-May net return, +1.434623 return after removing its best three
pre-May months, +0.236561 worst rolling six-month window, and a 0.118722 best
single-month share.

May 2026 benchmark after fixed pre-May selection:

- May-positive rows: 18.
- May-negative rows: 80.
- May-flat rows: 2.
- Best May return: +0.047219.
- Worst May return: -0.133646.
- Median May return: -0.016834.
- Mean May return: -0.020599.

May by dropout tier:

- `monthly_elite`: 78 rows, 13 positive, 65 negative, median -0.017857,
  mean -0.022260, best +0.015157, worst -0.133646.
- `dropout_robust`: 10 rows, 3 positive, 5 negative, 2 flat, median
  -0.000374, mean +0.005927, best +0.047219, worst -0.017119.
- `rolling_survivor`: 12 rows, 2 positive, 10 negative, median -0.023720,
  mean -0.031904, best +0.000845, worst -0.093322.

May-positive pockets:

- WPR106-146 cross-symbol relative-strength trade-veto variants: 2/2 selected
  rows positive in May, both +0.047219.
- WPR106-128 anchored VWAP variants: 3/3 selected rows positive in May, median
  +0.000845 and best +0.021960.
- WPR106-120 selected diversity/combo rows: 4/7 positive in May, median
  +0.003303, but mean -0.014053 because negative rows dominate.
- WPR106-119 contributes two positive rows, but the packet aggregate is still
  2/9 positive with median -0.024382.

May-negative concentration:

- WPR106-139 calendar/session rows remain 0/8 positive in May, median
  -0.037192 and worst -0.133646, even though they dominate the pre-May
  monthly-elite ranking.
- WPR106-156 recent complement portfolios remain 0/9 positive in May.
- WPR106-137 cross-symbol relative-strength/KNN-veto rows are 0/9 positive in
  May.
- WPR106-118 is 0/7 positive, WPR106-113 is 0/7 positive, and WPR106-136 is
  0/3 positive.

## Decision

The monthly dropout stability selector is rejected as candidate-ready,
portfolio-ready, or promotion-ready evidence. This is a direct falsification of
the idea that stricter pre-May monthly stability alone solves the May 2026
holdout fragility. The selected rows survive removing their best pre-May
months and many satisfy the target annual losing-month profile, but the fixed
May benchmark still has 80/100 losing rows, a negative median, and a negative
mean.

The packet preserves research-only follow-up pockets in WPR106-146
cross-symbol relative-strength trade-veto and WPR106-128 anchored VWAP rows.
Those pockets are not candidate-ready from this packet because they are small,
post-benchmark observations inside a failed aggregate selector, and May must
not become a tuning signal.

## Artifacts

- `data/research/wpr106_159_monthly_dropout_stability_selector/wpr106_159_monthly_dropout_stability_selector_summary.json`
- `data/research/wpr106_159_monthly_dropout_stability_selector/pre_may/artifact_inventory.parquet`
- `data/research/wpr106_159_monthly_dropout_stability_selector/pre_may/dropout_source_ranking.parquet`
- `data/research/wpr106_159_monthly_dropout_stability_selector/pre_may/dropout_source_top2500.csv`
- `data/research/wpr106_159_monthly_dropout_stability_selector/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_159_monthly_dropout_stability_selector/pre_may/selected_pre_may.csv`
- `data/research/wpr106_159_monthly_dropout_stability_selector/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_159_monthly_dropout_stability_selector/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_159_monthly_dropout_stability_selector/may_benchmark/selected_may_benchmark_metrics.csv`
- `data/research/wpr106_159_monthly_dropout_stability_selector/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_159_monthly_dropout_stability_selector/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_159_monthly_dropout_stability_selector/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_159_monthly_dropout_stability_selector/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
