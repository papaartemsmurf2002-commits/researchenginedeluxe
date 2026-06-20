# Stage R106 WPR106-210 Directional KNN Stability Reselection Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-210 revisited the discarded WPR106-190 directional KNN confidence-entry
universe. WPR106-190 had many annual-target rows and unusually positive
active May diagnostics, but its original selected set was mostly unstable or
May-inactive.

This packet did not change shared KNN, strategy, feature, backtest, live,
runtime, candidate-pack, or promotion code. It uses a packet-local runner to
re-rank WPR106-190 rows with stricter pre-May monthly controls, behavior
de-duplicate accepted trade paths, and replay May 2026 only after fixed
selection.

## Method

The artifact-only runner is:

- `data/research/wpr106_210_directional_knn_stability_reselection/scripts/run_wpr106_210_directional_knn_stability_reselection.py`

Inputs:

- WPR106-190 full pre-May ranking and monthly-return artifacts.
- WPR106-190/WPR106-170 source helpers for replaying selected rows.
- WPR106-96 BTCUSDT/ETHUSDT source contexts and KNN feature/label helpers.

All row scoring, tiering, preselection, and behavior de-duplication used only
2024-01-01 through 2026-04-30 UTC. May 2026 was benchmark-only.

The packet adds pre-May diagnostics for:

- latest Jan-April 2026 active-month and trade coverage;
- latest Jan-April 2026 return;
- drop-best-one-month and drop-best-three-month robustness;
- rolling three-month and six-month minimum returns;
- consecutive losing-month clusters;
- active-month median return.

Preselection tiers:

- `loose_recent_stability`: original WPR106-190 loose rows with recent
  activity, positive/near-positive robustness, and cost survival.
- `annual_sparse_control`: positive annual-target rows retained as controls
  only, with minimum sparse activity and recent participation.
- `active_positive_control`: active positive rows with recent coverage,
  cost survival, and bounded drawdown.

Preselected rows were replayed with accepted trades and behavior-deduplicated
by exact pre-May trade path before May benchmark.

Compute reused WPR106-190/WPR106-170 vectorized numpy KNN helper logic only
for selected unique tasks. CUDA was not used and no speedup was claimed.

## Results

Source WPR106-190 universe:

- Source rows: 23,328.
- Positive pre-May rows: 6,014.
- Positive annual-target rows: 2,396.
- Loose pre-May rows: 11.
- Strict pre-May rows: 0.
- Positive annual-target rows with at least 20 active months and 60 trades: 0.

The annual-target rows are therefore sparse controls, not active strategy
leads.

WPR106-210 reselection:

- Preselected rows: 240.
- Behavior-deduplicated selected rows: 100.
- Selected tiers: 96 `annual_sparse_control`, 4 `loose_recent_stability`.
- Selected symbols: 58 ETHUSDT, 42 BTCUSDT.

Selected pre-May replay:

- 100 positive rows, 0 negative rows, 0 flat rows.
- Median pre-May net return: +0.082670.
- Active mean pre-May net return: +0.087520.
- Best selected pre-May return: +0.347297.
- Worst selected pre-May return: +0.011914.

May 2026 benchmark after fixed selection:

- 100 benchmark rows.
- 1 active row, 99 flat rows.
- 0 positive rows, 1 negative row, 99 flat rows.
- Median May return: 0.000000.
- Active mean May return: -0.000946.
- Best May return: 0.000000.
- Worst May return: -0.000946.

The active May row was a BTCUSDT `cross_event_flow` Euclidean short inverse
momentum-continuation row. It had +0.058156 pre-May over 19 trades, 14 active
months, five losing months, annual loss counts 2/2/1, and -0.000946 in May
from one trade.

The strongest selected pre-May row was the WPR106-190 loose ETHUSDT
`cross_event_flow` Euclidean short inverse-volatility-breakout row with
+0.347297 pre-May over 60 trades, 24 active months, seven losing months,
annual loss counts 4/2/1, and no May trades.

## Decision

WPR106-210 rejects directional KNN stability reselection as candidate-ready,
portfolio-ready, paper/live-ready, or promotion-ready.

The WPR106-190 annual-target rows are not a hidden active lead: none has both
20 active months and 60 trades. When selected as controls, they do not
participate in May except for one losing trade. The active loose rows remain
pre-May unstable by the requested annual loss-month standard and are May
inactive after fixed selection.

The useful research evidence is narrower: WPR106-190's annual-target count was
driven by sparse rows, and the active directional-KNN ETHUSDT short pocket
still lacks May participation under stricter pre-May stability controls.

## Artifacts

- `data/research/wpr106_210_directional_knn_stability_reselection/wpr106_210_directional_knn_stability_reselection_summary.json`
- `data/research/wpr106_210_directional_knn_stability_reselection/pre_may/directional_knn_reselection_ranking.parquet`
- `data/research/wpr106_210_directional_knn_stability_reselection/pre_may/directional_knn_source_monthly_returns.parquet`
- `data/research/wpr106_210_directional_knn_stability_reselection/pre_may/family_summary.parquet`
- `data/research/wpr106_210_directional_knn_stability_reselection/pre_may/preselected_pre_may.parquet`
- `data/research/wpr106_210_directional_knn_stability_reselection/pre_may/preselected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_210_directional_knn_stability_reselection/pre_may/preselected_pre_may_trades.parquet`
- `data/research/wpr106_210_directional_knn_stability_reselection/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_210_directional_knn_stability_reselection/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_210_directional_knn_stability_reselection/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_210_directional_knn_stability_reselection/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_210_directional_knn_stability_reselection/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_210_directional_knn_stability_reselection/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_210_directional_knn_stability_reselection/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_210_directional_knn_stability_reselection/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_210_directional_knn_stability_reselection/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_210_directional_knn_stability_reselection/selected_pre_may_may_comparison.parquet`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_210_directional_knn_stability_reselection\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
