# WPR106-190 Directional KNN Confidence Entry Search

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the broad 2024-forward research search after WPR106-189 rejected
selectors over the WPR106-180 through WPR106-186 recent-family portfolio
universe. This packet pivots back to the Lorentzian/KNN family, but changes the
model formulation: instead of using KNN only as a veto over transparent event
signals, it tests KNN-generated directional confidence entries with transparent
event-template priors used as optional filters.

This is an artifact-only research packet, not a candidate-promotion packet.

## Scope

Selection/tuning window:

- 2024-01-01 through 2026-04-30 UTC.

Benchmark-only window:

- May 2026, replayed only after fixed pre-May row selection.

Inputs:

- WPR106-96 BTCUSDT/ETHUSDT 15m completed-bar and 1m aggTrade context.
- WPR106-170 feature, score, label, distance, accounting, and metrics helpers
  as packet-local imports.

Model/search family:

- Lorentzian and Euclidean neighbor geometry;
- path-quality and cross-event-flow feature packs;
- 8/16/32-bar fixed-hold path labels with completed labels only;
- KNN-generated signed confidence scores from long-vs-short neighbor mean
  return and good-rate spread;
- optional transparent event-template prior filters, including direct,
  inverse, and no-prior modes;
- recency and anti-crowding filters based on neighbor counts, confidence
  margin, session, target entries per active day, side mode, and daily caps;
- pre-May-only threshold calibration, ranking, and selection;
- May replay of fixed selected rows only.

May must not be used for feature choice, threshold choice, KNN parameter
choice, filter choice, row inclusion, daily-cap choice, or tie-breaking. May is
benchmark-only after fixed pre-May selection.

## Allowed Paths

- `docs/work_packets/WPR106-190-directional-knn-confidence-entry-search.md`
- `docs/stage_reports/STAGE_R106_DIRECTIONAL_KNN_CONFIDENCE_ENTRY_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/**`

## Plan

1. Import WPR106-170 helper functions for data loading, feature construction,
   KNN predictions, trade accounting, and metrics.
2. Build KNN directional confidence arrays from causal neighbor mean return and
   good-rate spreads for BTCUSDT/ETHUSDT.
3. Calibrate pre-May thresholds for active 1/3/5-entry-per-day targets, with
   optional transparent event priors used only as filters.
4. Evaluate pre-May candidate rows over distance, feature pack, hold,
   neighbor count, session, prior mode, side mode, confidence-margin, and daily
   cap grids.
5. Select fixed rows using only pre-May monthly stability, active-rate,
   cost-stress, annual-loss, drawdown, and concentration diagnostics.
6. Replay the fixed selected rows on May 2026.
7. Write ranking, selected pre-May, May benchmark, monthly/daily/trade
   artifacts, summary, report, ledger update, and validation notes.

## Research Boundary

All outputs remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_190_directional_knn_confidence_entry_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Closed on 2026-06-12 as a research-only diagnostic, not a candidate-ready
lead.

The packet-local runner
`data/research/wpr106_190_directional_knn_confidence_entry_search/scripts/run_wpr106_190_directional_knn_confidence_entry_search.py`
imports WPR106-170 data, feature, KNN, label, distance, accounting, and metric
helpers, but changes the model formulation to KNN-generated signed confidence
entries. It computes a confidence score from long-vs-short neighbor mean-return
spread plus good-rate spread, then optionally filters entries with direct or
inverse transparent event priors.

An initial broader 373,248-row grid was stopped before aggregate artifacts
after exceeding a 20-minute command timeout during pre-May evaluation. KNN
caches had completed; the bottleneck was redundant grid evaluation. The
completed bounded grid kept the stronger confidence-margin slice:

- `min_confidence_margin=0.0006`;
- `min_good_spread=0.08`;
- `recent_gate=none`.

Pre-May screen:

- 23,328 evaluated rows.
- 6,014 positive pre-May rows.
- 5,276 annual-target rows.
- 11 loose rows.
- 0 strict rows.

Fixed selected set:

- 100 selected rows.
- 8 `loose`, 92 `positive_stability`.
- 93 ETHUSDT rows and 7 BTCUSDT rows.
- Prior modes: 51 `knn_only`, 31 `direct_prior`, 18 `inverse_prior`.

Selected pre-May replay:

- 100 positive rows, 0 negative rows, 0 flat rows.
- Median net return: +0.347297.
- Active mean net return: +0.352858.
- Best/worst selected rows: +0.629334 / +0.124099.

May 2026 benchmark replay:

- 25 positive rows, 2 negative rows, 73 flat/no-trade rows.
- 27 active rows.
- Median net return across all rows: 0.000000.
- Active mean net return: +0.005054.
- Best/worst selected rows: +0.011793 / -0.015137.

The fixed selected set is rejected as candidate-ready, portfolio-ready, or
promotion-ready. It contains zero strict pre-May rows, most rows are fallback
`positive_stability`, and 73/100 rows are inactive in May. The active May
behavior is a useful diagnostic: ETHUSDT short directional-KNN rows, especially
`knn_only` and inverse volatility-breakout-prior variants, were mostly positive
when active. However, those rows have poor pre-May month stability, often 11 to
15 losing months and negative drop-best-three/rolling-six diagnostics, so they
need a May-blind stability repair or source-level control before they can be
treated as leads.

Artifacts:

- `data/research/wpr106_190_directional_knn_confidence_entry_search/pre_may/directional_knn_pre_may_ranking.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/pre_may/directional_knn_pre_may_monthly_returns.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/pre_may/selected_pre_may_rows.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/wpr106_190_directional_knn_confidence_entry_search_summary.json`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/wpr106_190_initial_timeout_stdout.log`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/wpr106_190_initial_timeout_stderr.log`

Validation passed:

```powershell
python -m compileall -q data\research\wpr106_190_directional_knn_confidence_entry_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
