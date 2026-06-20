# Stage R106 Broad Artifact Component Exposure Selector Report

Date: 2026-06-12
Packet: WPR106-157
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of artifact scoring, behavior de-duplication, rolling
diagnostics, component exposure caps, ranking, and selection. May was replayed
only after the fixed pre-May selected rows were written.

## Method

The runner
`data/research/wpr106_157_broad_artifact_component_exposure_selector/scripts/run_wpr106_157_broad_artifact_component_exposure_selector.py`
discovers local packet-shaped WPR106 artifacts under `data/research/wpr106_*`
that contain selected pre-May metrics, selected pre-May trade details, and May
benchmark trade details. It avoids broad recursive scans over unrelated cache
trees.

For each usable packet it normalizes source IDs such as `portfolio_id`,
`ensemble_id`, `overlay_id`, `candidate_id`, and `benchmark_id`; normalizes
net/gross/cost fields including weighted and portfolio returns; and recomputes
common metrics directly from selected trade details.

Selection uses only 2024-01-01 through 2026-04-30:

- accepted-trade behavior de-duplication by symbol, entry time, exit time, and
  side;
- monthly return metrics and annual loss counts;
- anchored rolling holdouts for 2024 Q4, 2025 Q1, 2025 Q2, 2025 Q3, 2025 Q4,
  and 2026 Jan-Apr;
- explicit packet, component, and symbol exposure caps;
- strict, rolling-robust, and loose pre-May tiers.

Compute used vectorized pandas artifact loading and grouped metric replay. No
CUDA path was used because this packet is an artifact-level selector, not a
new model/backtest grid, and no speedup was claimed.

## Results

Broad source universe:

- Discovered packet directories: 43.
- Included packet directories: 43.
- Loaded metric rows: 2,925.
- Loaded pre-May trade rows: 591,571.
- Loaded May benchmark trade rows: 21,216.
- Behavior-deduplicated source rows: 1,915.
- Positive pre-May rows: 1,915.
- Rolling-robust rows: 677.
- Loose rows: 1,126.
- Strict rows: 408.

Selected pre-May set:

- Selected rows: 100.
- Selection tiers: 70 `strict_rolling`, 29 `rolling_robust`, 1 `strict`.
- Selected packets: 23 packet labels.
- Largest packet exposures: 7 rows each from WPR106-139, WPR106-144,
  WPR106-137, WPR106-120, WPR106-119, WPR106-156, WPR106-118, WPR106-135, and
  WPR106-113.
- Trade-count range: 80 to 886.
- Active-month range: 21 to 28.
- Losing-month range: 1 to 10.
- Pre-May net-return range: +0.078470 to +2.480657.
- Rolling holdout positive-count range: 4 to 6.

The top pre-May row is WPR106-139
`calendar-31c7fbe72a20a7ac`, an ETHUSDT calendar flow impulse row with 678
trades, 28 active months, 4 losing months, annual losses 2024: 2, 2025: 1,
2026 Jan-Apr: 1, 5 of 6 positive rolling holdouts, +2.480657 pre-May net
return, -0.205831 max drawdown, and 4/4 cost-stress survival.

May 2026 benchmark after fixed pre-May selection:

- May-positive rows: 23.
- May-negative rows: 75.
- May-flat rows: 2.
- Best May return: +0.067949.
- Worst May return: -0.133646.
- Median May return: -0.014546.
- Mean May return: -0.018373.

May-positive pockets:

- WPR106-146 cross-symbol relative-strength trade-veto variants: 3/3 selected
  rows positive in May, best +0.067949 and median +0.067949.
- WPR106-128 anchored VWAP variants: 3/3 selected rows positive in May, median
  +0.006251.
- WPR106-120 selected diversity/combo rows: 4/7 positive in May, but mean May
  return is still negative because the negative rows dominate.
- WPR106-132 and WPR106-131 BTCUSDT trend/volatility-term variants: each 2/3
  selected rows positive in May, but too small and mixed to stand alone.
- WPR106-154 cross-symbol intrabar relative-pressure rows: 2/3 selected rows
  positive in May, best +0.043733, but the packet family remains mixed.

May-negative concentration:

- WPR106-139 calendar/session rows dominate the top pre-May ranking but are 0/7
  positive in May, with median -0.020699 and worst -0.133646.
- WPR106-137 diversity-constrained KNN-veto ensemble rows are 0/7 positive in
  this final selected set, despite strong pre-May strict-rolling diagnostics.
- WPR106-156 recent complement portfolios remain 0/7 positive in May.

## Decision

The broad artifact component exposure selector is rejected as candidate-ready
or portfolio-ready evidence. It is a stronger and wider falsification than the
recent-only WPR106-156 packet: it includes 43 local packet directories, applies
pre-May behavior de-duplication, rolling holdouts, and explicit exposure caps,
yet the fixed May benchmark still has a negative median and negative mean with
75 of 100 selected rows losing.

The packet does identify research-only follow-up pockets worth targeted
pre-May-only probing: WPR106-146 cross-symbol relative-strength trade-veto
variants, WPR106-128 anchored VWAP variants, and a smaller BTCUSDT
trend/volatility/cross-symbol intrabar pocket. These are not candidate-ready
because they are selected within a broad experiment whose aggregate holdout
failed, and any next probe must avoid using May as a tuning signal.

## Artifacts

- `data/research/wpr106_157_broad_artifact_component_exposure_selector/wpr106_157_broad_artifact_component_exposure_selector_summary.json`
- `data/research/wpr106_157_broad_artifact_component_exposure_selector/pre_may/artifact_inventory.parquet`
- `data/research/wpr106_157_broad_artifact_component_exposure_selector/pre_may/behavior_deduped_source_ranking.parquet`
- `data/research/wpr106_157_broad_artifact_component_exposure_selector/pre_may/behavior_deduped_source_top2500.csv`
- `data/research/wpr106_157_broad_artifact_component_exposure_selector/pre_may/behavior_deduped_source_monthly_returns.parquet`
- `data/research/wpr106_157_broad_artifact_component_exposure_selector/pre_may/family_summary.parquet`
- `data/research/wpr106_157_broad_artifact_component_exposure_selector/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_157_broad_artifact_component_exposure_selector/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_157_broad_artifact_component_exposure_selector/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_157_broad_artifact_component_exposure_selector/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_157_broad_artifact_component_exposure_selector/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_157_broad_artifact_component_exposure_selector/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_157_broad_artifact_component_exposure_selector/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
