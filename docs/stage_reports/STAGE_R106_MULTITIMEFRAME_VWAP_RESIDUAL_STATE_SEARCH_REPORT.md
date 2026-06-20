# Stage R106 WPR106-183 Multi-Timeframe VWAP Residual State Search Report

Status: closed
Date: 2026-06-12
Owner: Codex Research Agent

## Scope

WPR106-183 continued the 2024-forward broad research search with a transparent
multi-timeframe state family after the WPR106-182 KNN rejection. It combined
completed-bar VWAP distance, EMA trend, rolling volatility state, wick/flow
behavior, and BTC/ETH residual state.

Selection and ranking used only 2024-01-01 through 2026-04-30 UTC. May 2026
was benchmark-only after fixed pre-May selection.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/scripts/run_wpr106_183_multitimeframe_vwap_residual_state_search.py`

The runner reused WPR106-126 source-context loading, completed-bar alignment,
round-trip cost accounting, overlap handling, daily-cap handling, and metrics.
It tested BTCUSDT and ETHUSDT across:

- trend/VWAP pullback continuation;
- session VWAP reclaim/failure;
- rolling VWAP extension fade;
- BTC/ETH residual reversion;
- BTC/ETH residual momentum;
- volatility squeeze release follow.

The screen used 8/16/32/64-bar fixed holds, direct and inverse side policies,
all/Asia/EU/US sessions, all/trend-confirm/VWAP-dislocated/residual-extreme
state filters, all/compressed/expanding volatility filters, all/confirm/contra
/neutral flow filters, both/long/short side modes, 1/3/5 target raw signal
rates per day, and daily caps of 1/3/5. Feature definitions and threshold
calibration used completed bars only and excluded May from tuning.

To control compute, the runner first screened daily-cap-3 rows, then replayed
the strongest source pool across daily caps 1/3/5 with full monthly
diagnostics.

Runtime was 3269.59 seconds. CUDA was not used and no speedup claim was made.

## Results

Daily-cap-3 screen:

- 165,720 screened rows.
- 28,568 positive pre-May rows.
- 45 annual-target rows.
- 447 loose rows.
- 0 strict rows.

Full source-pool replay:

- 1,228 source rows expanded to 3,684 daily-cap rows.
- 3,653 positive pre-May rows.
- 129 annual-target rows.
- 1,240 loose rows.
- 0 strict rows.
- 100 selected rows: 90 `dropout_repair`, 10 `loose`.

Selected pre-May replay:

- 100 positive rows, 0 negative rows, 0 flat rows.
- Median net return: +1.011917.
- Active mean net return: +0.837380.
- Best/worst selected rows: +1.460809 / +0.183472.
- 63 unique pre-May trade-path hashes across 100 selected rows.
- Largest pre-May duplicate group: 6 rows.

May 2026 benchmark replay:

- 24 positive rows, 76 negative rows, 0 flat rows.
- Median net return: -0.031082.
- Active mean net return: -0.027420.
- Best/worst selected rows: +0.019486 / -0.094876.
- 31 unique May trade-path hashes across 100 selected rows.
- Largest May duplicate group: 9 rows.

The selected set is rejected. The best diagnostic May row is BTCUSDT
`squeeze_release_follow` direct-long EU-session residual-extreme compressed
state with flow-contra filtering and a 64-bar hold. It recorded +0.480141
pre-May across 156 trades with six losing months, then +0.019486 in May across
five trades. This remains only a research clue because there were no strict
pre-May rows, the selected set failed May, and repeated behavior variants
reduced independent evidence.

## Interpretation

The multi-timeframe VWAP/residual state family can produce profitable and
active pre-May rows, especially ETHUSDT inverse rolling-VWAP extension fades
and BTCUSDT squeeze-release/session-VWAP pockets. The May benchmark does not
confirm the family as configured. The pre-May selected set concentrated in a
few behavior clusters and transferred poorly to May despite strong pre-May
monthly diagnostics.

WPR106-183 therefore rejects the family as candidate-ready, portfolio-ready,
or promotion-ready. BTCUSDT squeeze-release and small BTC residual/session
VWAP May-positive pockets may be reused only as research clues in a later,
independently selected and behavior-deduplicated packet.

## Artifacts

- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/pre_may/screen_daily_cap3_ranking.parquet`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/pre_may/screen_daily_cap3_top3000.csv`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/pre_may/full_replay_source_pool.parquet`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/pre_may/multitimeframe_vwap_residual_state_ranking.parquet`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/pre_may/multitimeframe_vwap_residual_state_monthly_returns.parquet`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/pre_may/family_feature_summary.parquet`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/selected_pre_may_may_comparison_with_path_hashes.csv`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/wpr106_183_multitimeframe_vwap_residual_state_search_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_183_multitimeframe_vwap_residual_state_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
