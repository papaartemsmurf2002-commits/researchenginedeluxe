# Stage R106 WPR106-191 Directional KNN Accepted-Trade Stability Repair Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-191 followed WPR106-190 by testing whether May-blind accepted-trade
overlays could repair the directional KNN confidence entry lead without
creating new entries. It used the WPR106-190 selected pre-May and May accepted
trade ledgers plus selected source metrics.

All overlay calibration, confidence thresholds, good-spread thresholds, session
filters, extra daily caps, causal monthly gates, row ranking, and selected-row
inclusion used only 2024-01-01 through 2026-04-30 UTC. May 2026 was replayed
only after fixed pre-May overlay selection.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/scripts/run_wpr106_191_directional_knn_accepted_trade_stability_repair.py`

The runner imports the WPR106-190 implementation and WPR106-170 helper stack
for the WPR106-96 source context, embedded cost model, trade accounting,
monthly metrics, cost-stress diagnostics, and accepted-trade ledgers. It does
not generate new entries. Each overlay only filters WPR106-190 accepted trades
with:

- source-level absolute KNN confidence quantiles;
- source-level absolute good-spread quantiles;
- all, US, or non-US session filters;
- accepted-trade daily caps of 1 or 3;
- causal monthly gates based only on previously completed pre-May months.

An initial run failed after replay because the monthly diagnostic merge kept
computed column collisions and dropped expected diagnostic columns. A second
run completed but selected all May-flat overlays. The final run added explicit
recent Jan-Apr 2026 activity floors to selection; it still selected all
May-flat overlays.

The completed final run evaluated 19,200 overlay rows in 203.77 seconds. CUDA
was not used and no speedup claim was made.

## Results

Pre-May overlay screen:

- 100 WPR106-190 source rows.
- 19,200 evaluated overlay rows.
- 9,110 positive pre-May rows.
- 4,320 annual-target rows.
- 156 loose rows.
- 0 strict rows.

Fixed selected set:

- 100 selected rows.
- 70 `loose` rows and 30 `positive_stability` rows.
- 100 ETHUSDT rows.
- Monthly gates: 52 `none`, 20 `prev3_sum_nonnegative`, 18
  `prev1_nonnegative`, and 10 `prev3_loss_le1`.
- Session filters: 54 `all` and 46 `us`.

Selected pre-May replay:

- 100 positive rows, 0 negative rows, 0 flat rows.
- Median net return: +0.343498.
- Active mean net return: +0.365477.
- Best/worst selected rows: +0.770810 / +0.124099.

May 2026 benchmark replay:

- 0 active rows.
- 0 positive rows, 0 negative rows, 100 flat/no-trade rows.
- Median, active mean, best, and worst net return: 0.000000.

The top selected row was `knnrepair191-e339495d72af0f88`, sourced from
`dirknn190-423a669dcffc3ab8`: ETHUSDT, cross-event-flow, 16-bar hold,
Euclidean distance, k=31, KNN-only short, confidence q0.5, no good-spread
quantile threshold, all-session, `prev3_loss_le1`, daily cap 1. It had
+0.455082 pre-May over 189 trades, 21 active months, six losing months, four
active latest pre-May months, and 40 latest-four-month trades, but zero May
trades.

## Interpretation

WPR106-191 is rejected as a candidate, portfolio, or promotion lead. The
accepted-trade overlays can make WPR106-190 look materially more stable inside
the tuning window, but the fixed selected overlays do not trade at all in the
sealed May 2026 benchmark. This means the repair removed the only useful
WPR106-190 clue: limited but mostly positive active May behavior among ETHUSDT
short directional-KNN rows.

The result argues against spending another packet only on accepted-trade
filters over the WPR106-190 selected rows. Future work should either change the
source family, feature construction, KNN scoring, exit surface, or source-level
selection objective while preserving the May-blind rule.

## Artifacts

- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/pre_may/overlay_pre_may_calibration.parquet`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/pre_may/overlay_pre_may_calibration.csv`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/pre_may/overlay_pre_may_ranking.parquet`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/pre_may/overlay_pre_may_ranking.csv`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/pre_may/overlay_pre_may_monthly_returns.parquet`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/pre_may/selected_pre_may_overlays.parquet`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/pre_may/selected_pre_may_overlays.csv`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/pre_may/selected_pre_may_replay_metrics.csv`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/may_benchmark/selected_may_benchmark_metrics.csv`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/selected_pre_may_may_comparison.csv`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/wpr106_191_directional_knn_accepted_trade_stability_repair_summary.json`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/wpr106_191_initial_failed_stdout.log`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/wpr106_191_initial_failed_stderr.log`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/wpr106_191_initial_all_flat_selector_stdout.log`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/wpr106_191_initial_all_flat_selector_stderr.log`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/wpr106_191_run_stdout.log`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/wpr106_191_run_stderr.log`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_191_directional_knn_accepted_trade_stability_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
