# Stage R106 WPR106-186 Causal State Transition Edge Search Report

Status: closed
Date: 2026-06-12
Owner: Codex Research Agent

## Scope

WPR106-186 continued the broad 2024-forward strategy search after WPR106-185
rejected causal calendar-flow profiles. It tested causal market-state
transition edges over BTCUSDT and ETHUSDT 15m bars, using completed-bar
volatility state, trend state, VWAP displacement, BTC/ETH residual state, wick
state, session state, and aggTrade-flow state.

Selection and ranking used only 2024-01-01 through 2026-04-30 UTC. May 2026
was benchmark-only after fixed pre-May selection. May was not used for state
profile learning, parameter choice, row inclusion, ranking, or selection.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_186_causal_state_transition_edge_search/scripts/run_wpr106_186_causal_state_transition_edge_search.py`

The runner imported WPR106-185 rolling profile helpers and WPR106-183/WPR106-126
source, feature, and accounting helpers. State profiles were learned from
prior months only. May profiles were frozen from evidence through 2026-04-30.

The search covered:

- `vol_flow_trend`
- `residual_flow_trend`
- `vwap_residual_flow`
- `transition_vol_flow_trend`
- `flow_flip_trend_residual`
- `session_vol_flow_trend`

Each profile was tested across 3/6/12-month lookbacks, learned/long/short side
policies, 1/3/5 target raw signals per day, 8/16/32/64-bar holds, and daily
caps of 1/3/5 after source-pool expansion.

Runtime was 70.33 seconds. CUDA was not used and no speedup claim was made.

## Results

Screen:

- 1,296 rows.
- 37 positive pre-May rows.
- 15 annual-target rows, all too sparse or weak to become active-profile
  leads.
- 0 loose rows.
- 0 strict rows.

Full replay:

- 34 source rows expanded across daily caps 1/3/5.
- 102 replay rows.
- 89 positive pre-May rows.
- 0 annual-target rows.
- 0 loose rows.
- 0 strict rows.

Selected pre-May replay:

- 34 selected rows, all `positive_stability`.
- 34 positive rows, 0 negative rows, 0 flat rows.
- Median net return: +0.221411.
- Active mean net return: +0.234561.
- Best/worst selected rows: +0.511401 / +0.067338.

May 2026 benchmark replay:

- 18 positive rows, 16 negative rows, 0 flat rows.
- Median net return: +0.008596.
- Active mean net return: -0.019641.
- Best/worst selected rows: +0.055395 / -0.155169.
- Aggregate selected May total: -0.667796 across 439 trades.

By symbol, BTCUSDT was mixed but constructive at 12 positive and 3 negative
May rows, with median +0.009062 and mean +0.014794. ETHUSDT failed at 6
positive and 13 negative May rows, with median -0.050839 and mean -0.046827.

The strongest May diagnostic row was BTCUSDT `transition_vol_flow_trend`,
12-month lookback, short side policy, target one raw signal/day, 64-bar hold,
daily cap 1. It recorded +0.255860 pre-May across 189 trades with 12 losing
months, then +0.055395 in May across 12 trades. It remains only a research
clue because pre-May stability is weak: annual losses were 5/6/1, return after
dropping the best three months was -0.126062, and rolling six-month minimum
was -0.135838.

## Interpretation

The state-transition family is not candidate-ready. No full-replay rows met
loose or strict pre-May criteria, and selected rows were selected only as
positive-stability fallback rows. The May median was positive, but the active
mean was negative because several ETHUSDT state rows had large May losses.

BTCUSDT transition-state short profiles are a useful research-only clue for
later independent controls or a narrower BTC-only causal state family. The
current WPR106-186 family is rejected as candidate-ready, portfolio-ready, or
promotion-ready.

## Artifacts

- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/state_transition_edge_screen_ranking.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/state_transition_edge_screen_top1000.csv`
- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/state_transition_edge_screen_monthly_returns.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/state_transition_edge_full_replay_ranking.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/state_transition_edge_full_replay_ranking.csv`
- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/state_transition_edge_full_replay_monthly_returns.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/selected_pre_may_state_transition_edges.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/selected_pre_may_may_comparison.csv`
- `data/research/wpr106_186_causal_state_transition_edge_search/wpr106_186_causal_state_transition_edge_search_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_186_causal_state_transition_edge_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
