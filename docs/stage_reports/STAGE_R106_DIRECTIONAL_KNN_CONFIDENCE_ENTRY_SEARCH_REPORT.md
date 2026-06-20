# Stage R106 WPR106-190 Directional KNN Confidence Entry Search Report

Status: closed
Date: 2026-06-12
Owner: Codex Research Agent

## Scope

WPR106-190 continued the broad 2024-forward search after WPR106-189 rejected
selectors over the WPR106-180 through WPR106-186 recent-family portfolio
universe. It pivots back to the Lorentzian/KNN family with a different model
formulation: KNN-generated directional confidence entries rather than KNN as a
veto over transparent event signals.

All feature choice, KNN parameter choice, confidence thresholds, prior filters,
row ranking, daily-cap choice, and selected-row inclusion used only
2024-01-01 through 2026-04-30 UTC. May 2026 was benchmark-only after fixed
pre-May selection.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_190_directional_knn_confidence_entry_search/scripts/run_wpr106_190_directional_knn_confidence_entry_search.py`

The runner imports WPR106-170 helpers for the WPR106-96 source context, feature
matrices, Lorentzian/Euclidean distance, path labels, completed-label causal
neighbor pools, trade accounting, monthly metrics, and cost-stress diagnostics.
It changes the entry surface by computing a signed KNN confidence score from:

- long-vs-short neighbor mean-return spread;
- long-vs-short path-good-rate spread.

It then evaluates KNN-only, direct-prior, and inverse-prior variants against
transparent priors from momentum continuation, volatility-breakout
continuation, wick-flow absorption, and cross-symbol relative strength.

An initial broader 373,248-row grid was stopped before aggregate artifacts
after exceeding a 20-minute command timeout during pre-May evaluation. KNN
caches had completed; the bottleneck was redundant grid evaluation. The
completed bounded grid kept the stronger confidence-margin slice:

- `min_confidence_margin=0.0006`;
- `min_good_spread=0.08`;
- `recent_gate=none`.

The completed bounded run evaluated 23,328 rows. Runtime was 229.31 seconds.
CUDA was not used and no speedup claim was made.

## Results

Pre-May screen:

- 23,328 evaluated rows.
- 6,014 positive pre-May rows.
- 5,276 annual-target rows.
- 11 loose rows.
- 0 strict rows.

Pre-May screen by symbol:

- BTCUSDT: 11,664 rows, 2,212 positive, 2,686 annual-target, 3 loose, 0 strict,
  best +0.271864, median -0.066048.
- ETHUSDT: 11,664 rows, 3,802 positive, 2,590 annual-target, 8 loose, 0 strict,
  best +0.629334, median -0.028783.

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

May by selection tier:

- `loose`: 0 active rows, all 8 flat.
- `positive_stability`: 27 active rows, 25 positive and 2 negative, active
  mean +0.005054.

May by selected symbol/prior:

- BTCUSDT inverse-prior and KNN-only rows were all inactive in May.
- ETHUSDT direct-prior rows were all inactive in May.
- ETHUSDT inverse-prior rows had 4 active May rows, all positive, mean
  +0.001881 across all selected inverse-prior rows.
- ETHUSDT KNN-only rows had 23 active May rows, 21 positive, mean +0.002303
  across all selected KNN-only rows.

The best May row was `dirknn190-adf6fb190d3dc77f`: ETHUSDT, cross-event-flow,
8-bar hold, Euclidean distance, k=11, all-session short, inverse volatility
breakout prior, daily cap 3. It had +0.162055 pre-May over 84 trades, but 12
pre-May losing months, seven losing months in 2024, and only +0.011793 in May
from one trade.

## Interpretation

Directional KNN confidence entries are a useful diagnostic but not a
candidate-ready lead. Compared with the recent-family portfolio selectors, the
active May behavior is less uniformly bad: 25 of 27 active May rows were
positive. But the selected set fails the requested stability standard:

- zero strict pre-May rows;
- only 11 loose rows out of 23,328 evaluated rows;
- selected rows are mostly fallback `positive_stability`;
- many ETHUSDT short rows have 11 to 15 pre-May losing months;
- 73/100 selected rows are inactive in May;
- the best May row is one trade, not a robust month.

WPR106-190 therefore rejects the bounded directional-KNN confidence entry
search as candidate-ready, portfolio-ready, or promotion-ready. It preserves
ETHUSDT short directional-KNN behavior, especially KNN-only and inverse
volatility-breakout-prior variants, as a research-only diagnostic for a
follow-up May-blind source-level stability repair or feature/filter control.

## Artifacts

- `data/research/wpr106_190_directional_knn_confidence_entry_search/pre_may/directional_knn_pre_may_ranking.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/pre_may/directional_knn_pre_may_ranking.csv`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/pre_may/directional_knn_pre_may_monthly_returns.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/pre_may/selected_pre_may_rows.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/pre_may/selected_pre_may_rows.csv`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/pre_may/selected_pre_may_replay_metrics.csv`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/may_benchmark/selected_may_benchmark_metrics.csv`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/selected_pre_may_may_comparison.csv`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/wpr106_190_directional_knn_confidence_entry_search_summary.json`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/wpr106_190_initial_timeout_stdout.log`
- `data/research/wpr106_190_directional_knn_confidence_entry_search/wpr106_190_initial_timeout_stderr.log`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_190_directional_knn_confidence_entry_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
