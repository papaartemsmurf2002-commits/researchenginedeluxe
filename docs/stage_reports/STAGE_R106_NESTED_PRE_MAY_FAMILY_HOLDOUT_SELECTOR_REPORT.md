# Stage R106 Nested Pre-May Family Holdout Selector Report

Date: 2026-06-12
Packet: WPR106-158
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of ranking, nested diagnostics, family/component scoring,
exposure caps, and selection. May was replayed only after the fixed pre-May
selected rows were written.

## Method

The runner
`data/research/wpr106_158_nested_pre_may_family_holdout_selector/scripts/run_wpr106_158_nested_pre_may_family_holdout_selector.py`
reuses the WPR106-157 artifact-universe builder, which normalizes local
WPR106 selected artifacts, behavior-de-duplicates accepted pre-May trade paths,
and recomputes common metrics from trade details.

Selection uses only 2024-01-01 through 2026-04-30:

- early pre-May diagnostics for 2024-01 through 2025-06;
- late validation diagnostics for 2025-07 through 2026-04;
- 2024, 2025, and 2026 Jan-Apr year blocks;
- six anchored pre-May rolling holdouts inherited from WPR106-157;
- component/family scores based on late-positive rates, year balance, rolling
  evidence, drawdown, cost stress, and active but capped trade rates;
- packet, component, symbol, and behavior exposure caps.

The selector writes three pre-May tiers: `strict_nested`, `robust_nested`, and
`late_resilient`. The `late_resilient` tier is a fill tier, not a candidate
claim.

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
- Strict nested rows: 367.
- Robust nested rows: 588.
- Late-resilient rows: 1,351.

Selected pre-May set:

- Selected rows: 100.
- Selection tiers: 69 `strict_nested`, 30 `robust_nested`, 1
  `late_resilient`.
- Largest packet exposures: 7 rows each from WPR106-139, WPR106-144,
  WPR106-156, WPR106-118, WPR106-119, WPR106-137, WPR106-135, and
  WPR106-120.
- Trade-count range: 80 to 1,241.
- Active-month range: 22 to 28.
- Losing-month range: 1 to 11.
- Pre-May total net-return range: +0.077980 to +2.480657.
- Early pre-May return range: +0.023570 to +1.713731.
- Late pre-May return range: +0.021817 to +0.937706.
- Late losing-month range: 0 to 4.
- Max-drawdown range: -0.315592 to -0.003451.

The top nested pre-May row is WPR106-139
`calendar-ad953bfdaa925347`, an ETHUSDT calendar session momentum row with
488 trades, 28 active months, 4 losing months, annual losses 2024: 2,
2025: 1, 2026 Jan-Apr: 1, +1.290213 early pre-May return, +0.937706 late
pre-May return, +2.227919 total pre-May net return, -0.196723 max drawdown,
and 4/4 cost-stress survival.

May 2026 benchmark after fixed pre-May selection:

- May-positive rows: 23.
- May-negative rows: 75.
- May-flat rows: 2.
- Best May return: +0.067949.
- Worst May return: -0.133646.
- Median May return: -0.017069.
- Mean May return: -0.020578.

May by nested tier:

- `strict_nested`: 69 rows, 11 positive, 58 negative, median -0.020852,
  mean -0.022766, best +0.067949, worst -0.133646.
- `robust_nested`: 30 rows, 11 positive, 17 negative, 2 flat, median
  -0.008169, mean -0.016857, best +0.033449, worst -0.127690.
- `late_resilient`: 1 row, 1 positive, median and mean +0.018723.

May-positive pockets:

- WPR106-146 cross-symbol relative-strength trade-veto variants: 3/3 selected
  rows positive in May, best +0.067949 and worst +0.051377.
- WPR106-131 BTCUSDT volatility-term and volatility-expansion variants: 3/4
  rows positive, median +0.006138, best +0.023233.
- WPR106-120 selected diversity/combo rows: 4/7 rows positive, median
  +0.003303, but mean -0.018220 because negative rows dominate.
- WPR106-128 anchored VWAP variants: 4/6 rows positive and 1 flat, median
  +0.000845, but mean -0.009850 because one row loses -0.127690.
- WPR106-111, WPR106-132, and one WPR106-109 row are positive, but the sample
  sizes are too small to stand alone.

May-negative concentration:

- WPR106-139 calendar/session rows dominate the nested pre-May ranking but are
  0/7 positive in May, median -0.041362 and worst -0.133646.
- WPR106-137 cross-symbol relative-strength/KNN-veto rows are 0/7 positive in
  May, median -0.020852.
- WPR106-156 recent complement portfolios remain 0/7 positive in May, median
  -0.029090.
- WPR106-118 and WPR106-119 are each 0/7 positive in May, with medians
  -0.029918 and -0.033490.
- WPR106-113 is 0/6 positive in May, median -0.024016.
- WPR106-136 is 0/3 positive in May, all -0.070820.

## Decision

The nested pre-May family holdout selector is rejected as candidate-ready,
portfolio-ready, or promotion-ready evidence. The stricter pre-May nested
diagnostics improved the pre-May selected set on paper, but May still rejects
the fixed selected set with 75/100 losing rows, a negative median, and a
negative mean. The result shows that late pre-May validation, annual balance,
rolling holdouts, behavior de-duplication, and exposure caps are still
insufficient as a selector over the current artifact universe.

The packet preserves research-only leads for future May-blind probing:
WPR106-146 cross-symbol relative-strength trade-veto variants remain the
clearest small positive May pocket, and WPR106-131/128/120 contain smaller
mixed pockets. These cannot be promoted from this packet because the aggregate
holdout failed and May must not become a tuning signal.

## Artifacts

- `data/research/wpr106_158_nested_pre_may_family_holdout_selector/wpr106_158_nested_pre_may_family_holdout_selector_summary.json`
- `data/research/wpr106_158_nested_pre_may_family_holdout_selector/pre_may/artifact_inventory.parquet`
- `data/research/wpr106_158_nested_pre_may_family_holdout_selector/pre_may/nested_source_ranking.parquet`
- `data/research/wpr106_158_nested_pre_may_family_holdout_selector/pre_may/nested_source_top2500.csv`
- `data/research/wpr106_158_nested_pre_may_family_holdout_selector/pre_may/component_diagnostics.parquet`
- `data/research/wpr106_158_nested_pre_may_family_holdout_selector/pre_may/family_summary.parquet`
- `data/research/wpr106_158_nested_pre_may_family_holdout_selector/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_158_nested_pre_may_family_holdout_selector/pre_may/selected_pre_may.csv`
- `data/research/wpr106_158_nested_pre_may_family_holdout_selector/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_158_nested_pre_may_family_holdout_selector/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_158_nested_pre_may_family_holdout_selector/may_benchmark/selected_may_benchmark_metrics.csv`
- `data/research/wpr106_158_nested_pre_may_family_holdout_selector/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_158_nested_pre_may_family_holdout_selector/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_158_nested_pre_may_family_holdout_selector/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_158_nested_pre_may_family_holdout_selector/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
