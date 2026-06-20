# Stage R106 WPR133 Behavior-Dedup Stability Controls Report

Date: 2026-06-12
Packet: WPR106-147
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was not used for behavior de-duplication, rolling-selection rules,
sibling-source controls, hedge settings, parameter ranking, or any tuning
decision. May was replayed only after fixed pre-May definitions were written.

## Method

The runner
`data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/scripts/run_wpr106_147_wpr133_behavior_dedup_stability_controls.py`
imports the WPR106-146 and WPR106-136 artifact helpers and re-evaluates the
WPR106-146 target source `wpr133_leadlag:leadlag-18708dffa1413dce`.

Controls:

- recompute the 12,000-row target KNN parameter grid with accepted-trade
  behavior hashes;
- deduplicate by pre-May behavior hash, keeping one pre-May representative per
  trade path;
- run anchored rolling pre-May train/holdout selections over six fixed
  holdout slices;
- replay the top behavior-deduped pre-May rows on May 2026;
- apply the top five behavior-deduped parameter settings to all 14 WPR106-133
  ETHUSDT relative-strength continuation source rows;
- run diagnostic BTC hedge variants at fixed hedge weights 0.25, 0.50, and
  1.00 for the top five selected rows.

## Results

Behavior de-duplication:

- Parameter grid rows: 12,000.
- Unique pre-May behavior hashes: 2,340.
- Grid profile-ok rows before behavior de-duplication: 4,377.
- Grid strict-like rows before behavior de-duplication: 45.
- Grid WPR106-136 strict rows before behavior de-duplication: 30.
- Behavior-deduped representatives: 2,340.
- Behavior-deduped profile-ok representatives: 718.
- Behavior-deduped strict-like representatives: 15.

The top behavior-deduped row remains the WPR106-146 leading variant:

- `regime_reversal` feature pack;
- Lorentzian distance;
- 64-trade lookback;
- 31 neighbors;
- same-side history;
- neighbor mean threshold -0.00025;
- neighbor win-rate threshold 0.46;
- daily cap 3;
- 242 pre-May trades;
- 25 active months;
- 4 losing months;
- annual losses 2024: 2, 2025: 2, 2026 Jan-Apr: 0;
- +1.140510 pre-May net return;
- -0.145973 max drawdown;
- +0.067949 May with 16 trades.

Top behavior-deduped May benchmark:

- Selected behavior-deduped rows: 30.
- Selected rows May-positive: 30/30.
- Selected rows passing pre-May profile and May benchmark: 30/30.
- Best selected May: +0.067949.
- Median selected May: +0.034110.
- Worst selected May: +0.015398.

Rolling pre-May selection:

- Six anchored train/holdout splits were evaluated.
- Top-1 rolling selections were holdout-positive in 3/6 splits.
- Top-1 rolling selections were holdout profile-ok in 3/6 splits.
- Top-3 equal-average rolling selections were holdout-positive in 3/6 splits.
- The failed holdouts were 2025 Q1, 2025 Q2, and 2025 Q3. The worst top-1
  holdout was 2025 Q3 at -0.096430.

Sibling source controls:

- Source-control rows: 70, covering five parameter settings across 14 sibling
  ETHUSDT relative-strength continuation source rows.
- Target-source rows pass pre-May and May in 5/5 controls.
- Non-target sibling rows: 65.
- Non-target sibling profile-ok rows: 9.
- Non-target sibling strict-like rows: 0.
- Non-target sibling May-positive rows: 23.
- Non-target sibling rows passing both pre-May profile and May benchmark: 0.
- The strongest sibling May-positive rows fail pre-May stability, while the
  sibling rows with profile-ok pre-May behavior are May-negative.

BTC hedge diagnostics:

- Hedge rows: 15.
- Hedge pre-May profile-ok rows: 4.
- Hedge strict-like rows: 0.
- Hedge May-positive rows: 10.
- A 0.25 BTC hedge keeps the top two rows May-positive and profile-ok but adds
  a third 2024 losing month, breaking strict-like annual stability.
- A 1.00 BTC hedge makes the top rows May-negative and usually fails pre-May
  profile checks.

## Decision

WPR106-147 rejects the WPR106-146 lead as a broader source-level strategy. The
fixed top behavior-deduped rows still look good when selected on the full
pre-May window and then benchmarked on May, but rolling pre-May selection fails
half of the internal holdouts, the same KNN settings do not transfer to
neighboring WPR106-133 relative-strength source rows, and BTC hedge diagnostics
weaken rather than improve stability.

The result remains useful research evidence: the target source has a real
path-specific pocket, but the evidence is too path-coupled for a candidate
attempt. The next broad-search work should move away from defending this exact
source path and either test different WPR106-133 feature construction/exit
logic from scratch or return to other discarded families with behavior-deduped
rolling holdout controls built in from the start.

## Artifacts

- `data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/wpr106_147_wpr133_behavior_dedup_stability_controls_summary.json`
- `data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/selected_behavior_deduped_metrics.parquet`
- `data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/selected_behavior_deduped_metrics.csv`
- `data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/sibling_source_control_metrics.parquet`
- `data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/sibling_source_control_metrics.csv`
- `data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/btc_hedge_diagnostics.parquet`
- `data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/btc_hedge_diagnostics.csv`
- `data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/pre_may/target_parameter_grid_with_behavior.parquet`
- `data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/pre_may/target_parameter_grid_with_behavior_top1000.csv`
- `data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/pre_may/target_parameter_grid_monthly_returns.parquet`
- `data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/pre_may/behavior_deduped_parameter_representatives.parquet`
- `data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/pre_may/behavior_deduped_parameter_representatives_top1000.csv`
- `data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/pre_may/rolling_pre_may_holdout_selection.parquet`
- `data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/pre_may/rolling_pre_may_holdout_top3_portfolios.parquet`
- `data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/may_benchmark/selected_behavior_deduped_monthly_returns.parquet`
- `data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/may_benchmark/selected_behavior_deduped_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_147_wpr133_behavior_dedup_stability_controls/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
