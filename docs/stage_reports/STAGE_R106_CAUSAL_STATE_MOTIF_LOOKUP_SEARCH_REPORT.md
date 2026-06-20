# Stage R106 WPR106-192 Causal State Motif Lookup Search Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-192 continued the broad 2024-forward search after WPR106-191 rejected
accepted-trade overlays over WPR106-190 directional KNN rows. It tested a fresh
non-KNN source family: causal rolling state/motif lookup entries built from
completed 15m bar path, wick/range, volatility, session, cross-symbol, and
aggTrade-flow states.

All motif definitions, feature buckets, hold/lookback choices, side modes,
session filters, thresholds, daily caps, row ranking, and selected-row
inclusion used only 2024-01-01 through 2026-04-30 UTC. May 2026 was replayed
only after fixed pre-May selection.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_192_causal_state_motif_lookup_search/scripts/run_wpr106_192_causal_state_motif_lookup_search.py`

The runner loads WPR106-96 BTCUSDT/ETHUSDT source contexts through WPR106-170
helpers and reuses the WPR106 embedded cost model, fixed-hold path labels,
same-symbol overlap blocking, daily-cap handling, monthly metrics, drawdown,
Sortino, annual losing-month targets, and cost-stress diagnostics.

The model is not KNN. It encodes completed-bar motif keys and uses cumulative
prior-history lookup tables for long/short mean net return and path-good rate.
For pre-May rows, the lookup uses only prior completed labels inside the
configured rolling lookback. For May benchmark rows, the lookup state is frozen
to pre-May history only, so May labels are not used for adaptation.

An initial broader 64,800-row grid was stopped after a 15-minute command
timeout at 55,000 evaluated pre-May rows before aggregate artifacts were
written. The final bounded grid kept:

- motif packs: `path_flow`, `cross_residual`, `flow_absorption`,
  `trend_pullback_clock`;
- holds: 8, 16, and 32 bars;
- lookbacks: 6,144 and 12,288 bars;
- side modes: both, long, and short;
- sessions: all, EU, and US;
- daily caps: 1, 3, and 5.

The bounded run evaluated 5,184 rows in 118.17 seconds. CUDA was not used and
no speedup claim was made.

## Results

Pre-May screen:

- 5,184 evaluated rows.
- 242 positive pre-May rows.
- 43 annual-target rows.
- 0 loose rows.
- 0 strict rows.

Pre-May by symbol:

- BTCUSDT: 2,592 rows, 108 positive, 33 annual-target, 0 loose, 0 strict,
  best +0.171020, median -0.340469.
- ETHUSDT: 2,592 rows, 134 positive, 10 annual-target, 0 loose, 0 strict,
  best +0.489121, median -0.516135.

Pre-May by motif:

- `cross_residual`: 1,296 rows, 40 positive, 4 annual-target, best +0.489121.
- `trend_pullback_clock`: 1,296 rows, 74 positive, 6 annual-target, best
  +0.461695.
- `path_flow`: 1,296 rows, 61 positive, 0 annual-target, best +0.419759.
- `flow_absorption`: 1,296 rows, 67 positive, 33 annual-target, best +0.139556.

Fixed selected set:

- 74 selected rows.
- All 74 are `positive_recent_stability` fallback rows.
- 62 ETHUSDT rows and 12 BTCUSDT rows.
- Motif mix: 36 `trend_pullback_clock`, 15 `path_flow`, 13
  `flow_absorption`, and 10 `cross_residual`.

Selected pre-May replay:

- 74 positive rows, 0 negative rows, 0 flat rows.
- Median net return: +0.205355.
- Active mean net return: +0.223349.
- Best/worst selected rows: +0.489121 / +0.028659.

May 2026 benchmark replay:

- 74 active rows.
- 45 positive rows and 29 negative rows.
- Median net return: +0.008759.
- Active mean net return: +0.015506.
- Best/worst selected rows: +0.090413 / -0.030529.

May by selected symbol/motif:

- ETHUSDT `trend_pullback_clock`: 34 rows, 28 positive and 6 negative, May
  median +0.026387, best +0.090413.
- ETHUSDT `cross_residual`: 10 rows, 6 positive and 4 negative, May median
  +0.011492.
- ETHUSDT `flow_absorption`: 6 rows, all positive, May median +0.008759.
- ETHUSDT `path_flow`: 12 rows, 5 positive and 7 negative, May median
  -0.003666.
- All selected BTCUSDT motif groups were May-negative.

The best May row was `motif192-e04007619d5902f3`: ETHUSDT,
`trend_pullback_clock`, 32-bar hold, 6,144-bar lookback, US session,
both-sided, daily cap 3. It had +0.439334 pre-May over 718 trades, 28 active
months, and +0.090413 in May over 40 trades, but it also had 14 pre-May losing
months, seven losing months in 2024, six in 2025, one in 2026 Jan-Apr, and
max drawdown -0.439939.

The 43 annual-target rows were not usable leads. They were sparse and not
recently active; none passed latest-four-month floors of at least two active
months and at least 12 trades.

## Interpretation

WPR106-192 is rejected as candidate-ready, portfolio-ready, or
promotion-ready. It found a different failure shape from WPR106-188 through
WPR106-191: selected rows did remain active in May, and the ETHUSDT
US-session `trend_pullback_clock` pocket had positive May transfer. But the
pre-May evidence is not stable enough for the requested profile:

- zero strict rows and zero loose rows;
- selected rows are all fallback positive-stability rows;
- annual-target rows are sparse and stale;
- the strongest May rows have excessive pre-May losing months;
- drawdowns around the best ETHUSDT pocket are too large;
- BTCUSDT selected rows were all May-negative.

The useful diagnostic is that simple causal state motifs can produce active
May transfer without using May for selection. The current bounded formulation
does not solve month-to-month stability, so any future follow-up should change
the source/risk-control logic rather than promote these rows.

## Artifacts

- `data/research/wpr106_192_causal_state_motif_lookup_search/pre_may/motif_lookup_pre_may_ranking.parquet`
- `data/research/wpr106_192_causal_state_motif_lookup_search/pre_may/motif_lookup_pre_may_ranking.csv`
- `data/research/wpr106_192_causal_state_motif_lookup_search/pre_may/motif_lookup_pre_may_monthly_returns.parquet`
- `data/research/wpr106_192_causal_state_motif_lookup_search/pre_may/selected_pre_may_rows.parquet`
- `data/research/wpr106_192_causal_state_motif_lookup_search/pre_may/selected_pre_may_rows.csv`
- `data/research/wpr106_192_causal_state_motif_lookup_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_192_causal_state_motif_lookup_search/pre_may/selected_pre_may_replay_metrics.csv`
- `data/research/wpr106_192_causal_state_motif_lookup_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_192_causal_state_motif_lookup_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_192_causal_state_motif_lookup_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_192_causal_state_motif_lookup_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_192_causal_state_motif_lookup_search/may_benchmark/selected_may_benchmark_metrics.csv`
- `data/research/wpr106_192_causal_state_motif_lookup_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_192_causal_state_motif_lookup_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_192_causal_state_motif_lookup_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_192_causal_state_motif_lookup_search/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_192_causal_state_motif_lookup_search/selected_pre_may_may_comparison.csv`
- `data/research/wpr106_192_causal_state_motif_lookup_search/wpr106_192_causal_state_motif_lookup_search_summary.json`
- `data/research/wpr106_192_causal_state_motif_lookup_search/wpr106_192_run_stdout.log`
- `data/research/wpr106_192_causal_state_motif_lookup_search/wpr106_192_run_stderr.log`
- `data/research/wpr106_192_causal_state_motif_lookup_search/wpr106_192_broad_timeout_stdout.log`
- `data/research/wpr106_192_causal_state_motif_lookup_search/wpr106_192_broad_timeout_stderr.log`
- `data/research/wpr106_192_causal_state_motif_lookup_search/wpr106_192_bounded_run_stdout.log`
- `data/research/wpr106_192_causal_state_motif_lookup_search/wpr106_192_bounded_run_stderr.log`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_192_causal_state_motif_lookup_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
