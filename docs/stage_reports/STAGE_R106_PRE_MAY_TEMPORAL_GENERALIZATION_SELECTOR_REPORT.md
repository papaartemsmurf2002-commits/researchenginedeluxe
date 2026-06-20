# Stage R106 Pre-May Temporal Generalization Selector Report

Date: 2026-06-12
Packet: WPR106-160
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of train scoring, 2026 Jan-Apr validation scoring,
dropout scoring, annual loss limits, exposure caps, ranking, and selection.
May was replayed only after the fixed pre-May selected rows were written.

## Method

The runner
`data/research/wpr106_160_pre_may_temporal_generalization_selector/scripts/run_wpr106_160_pre_may_temporal_generalization_selector.py`
reuses the WPR106-157 artifact-universe builder, which normalizes local WPR106
selected artifacts, behavior-de-duplicates accepted pre-May trade paths, and
recomputes common metrics from trade details.

Selection uses only 2024-01-01 through 2026-04-30:

- search history: 2024-01 through 2025-12;
- final pre-May validation gate: 2026-01 through 2026-04;
- 2024 and 2025 annual losing-month caps;
- 2026 Jan-Apr active-month, losing-month, and worst-month checks;
- 2024-2025 best-month dropout and rolling six-month stability;
- cost stress, drawdown, active trade-rate, and concentration filters;
- packet, component, symbol, and behavior exposure caps.

The selector writes three pre-May tiers: `temporal_elite`,
`temporal_robust`, and `validation_survivor`. The `temporal_elite` tier
requires positive 2024-2025 search return, positive 2026 Jan-Apr validation
return, no more than one 2026 Jan-Apr losing month, positive search return
after dropping the best three search months, non-negative rolling six-month
search windows, and active rates at or below five trades per active day.

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
- Temporal-elite rows: 321.
- Temporal-robust rows: 475.
- Validation-survivor rows: 873.

Selected pre-May set:

- Selected rows: 100.
- Selection tiers: 78 `temporal_elite`, 13 `temporal_robust`, and 9
  `validation_survivor`.
- Largest packet exposures: 9 rows each from WPR106-139, WPR106-144,
  WPR106-137, WPR106-135, and WPR106-156.
- Trade-count range: 85 to 985.
- Active-month range: 21 to 28.
- 2024-2025 search return range: +0.048081 to +2.038350.
- 2026 Jan-Apr validation return range: +0.000792 to +0.531043.
- 2026 Jan-Apr losing-month range: 0 to 2.
- Search drop-best-three return range: +0.030149 to +1.188448.
- Search rolling six-month worst-window range: -0.046285 to +0.328204.
- Pre-May total net-return range: +0.053276 to +2.480657.
- Max-drawdown range: -0.359124 to -0.002712.

The top pre-May row is WPR106-139 `calendar-31c7fbe72a20a7ac`, an ETHUSDT
calendar flow impulse row with 678 trades, +2.038350 search return, +0.442307
2026 Jan-Apr validation return, one validation losing month, +1.188448 search
return after removing the best three search months, +0.324619 worst rolling
six-month search window, and +2.480657 total pre-May net return.

May 2026 benchmark after fixed pre-May selection:

- May-positive rows: 20.
- May-negative rows: 78.
- May-flat rows: 2.
- Best May return: +0.067949.
- Worst May return: -0.133646.
- Median May return: -0.017037.
- Mean May return: -0.019105.

May by temporal tier:

- `temporal_elite`: 78 rows, 16 positive, 62 negative, median -0.017037,
  mean -0.017914, best +0.067949, worst -0.133646.
- `temporal_robust`: 13 rows, 4 positive, 7 negative, 2 flat, median
  -0.010441, mean -0.008536, best +0.033449, worst -0.051256.
- `validation_survivor`: 9 rows, 0 positive, 9 negative, median -0.037253,
  mean -0.044694, best -0.010519, worst -0.109560.

May-positive pockets:

- WPR106-146 cross-symbol relative-strength trade-veto variants: 4/4 selected
  rows positive in May, median +0.041673, best +0.067949, worst +0.015398.
- WPR106-128 anchored VWAP variants: 3/3 selected rows positive in May, median
  +0.033449, best +0.033449, worst +0.000845.
- WPR106-120 selected diversity/combo rows: 4/7 selected rows positive in May,
  median +0.003303, but mean -0.014053 because negative rows dominate.
- WPR106-121 contributed one positive failed-expansion fade row, but the
  packet-level result was 1/3 positive with median -0.051256.

May-negative concentration:

- WPR106-139 calendar/session and calendar-flow rows remain 0/9 positive in
  May, median -0.033021 and worst -0.133646, despite dominating the pre-May
  temporal ranking.
- WPR106-156 recent complement portfolios remain 0/9 positive in May.
- WPR106-137 cross-symbol relative-strength/KNN-veto rows are 0/9 positive in
  May.
- WPR106-118 is 0/7 positive, WPR106-113 is 0/7 positive, and WPR106-108 is
  0/4 positive.

## Decision

The pre-May temporal generalization selector is rejected as candidate-ready,
portfolio-ready, or promotion-ready evidence. Adding an explicit 2026 Jan-Apr
validation gate inside the pre-May window did not solve the May holdout
fragility. The fixed selected set had positive 2024-2025 search returns,
positive 2026 Jan-Apr validation returns, and mostly clean validation monthly
profiles, but the May benchmark still had 78/100 losing rows with negative
median and mean returns.

The packet preserves research-only follow-up pockets in WPR106-146
cross-symbol relative-strength trade-veto and WPR106-128 anchored VWAP rows.
Those pockets are not candidate-ready from this packet because they are small
and are being observed after the fixed benchmark, not selected with May. Future
work must test them through May-blind pre-May specifications and controls
rather than tune toward their observed May behavior.

## Artifacts

- `data/research/wpr106_160_pre_may_temporal_generalization_selector/wpr106_160_pre_may_temporal_generalization_selector_summary.json`
- `data/research/wpr106_160_pre_may_temporal_generalization_selector/pre_may/artifact_inventory.parquet`
- `data/research/wpr106_160_pre_may_temporal_generalization_selector/pre_may/temporal_source_ranking.parquet`
- `data/research/wpr106_160_pre_may_temporal_generalization_selector/pre_may/temporal_source_top2500.csv`
- `data/research/wpr106_160_pre_may_temporal_generalization_selector/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_160_pre_may_temporal_generalization_selector/pre_may/selected_pre_may.csv`
- `data/research/wpr106_160_pre_may_temporal_generalization_selector/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_160_pre_may_temporal_generalization_selector/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_160_pre_may_temporal_generalization_selector/may_benchmark/selected_may_benchmark_metrics.csv`
- `data/research/wpr106_160_pre_may_temporal_generalization_selector/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_160_pre_may_temporal_generalization_selector/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_160_pre_may_temporal_generalization_selector/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_160_pre_may_temporal_generalization_selector/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
