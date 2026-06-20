# Stage R106 Multi-Horizon Trend State Search Report

Date: 2026-06-11
Packet: WPR106-132
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of all feature, threshold, filter, hold, ranking, and
selection decisions. May was replayed only after fixed loose pre-May selection,
because no strict pre-May rows existed.

## Method

The runner
`data/research/wpr106_132_multi_horizon_trend_state_search/scripts/run_wpr106_132_multi_horizon_trend_state_search.py`
uses WPR106-126 source-context loading over WPR106-96 public-archive BTCUSDT
and ETHUSDT bars plus 15m aggTrade-flow aggregation.

Each symbol has 84,672 15m bars from 2024-01-01 through 2026-05-31. Signals
use completed 15m bars and enter on the next 15m open. Pre-May trades are
required to exit before 2026-05-01.

The grid covers:

- State windows: 96, 384, and 1,536 bars.
- Fixed holds: 4, 8, 16, and 32 bars.
- Sessions: all, Asia, EU, and US.
- State filters: all, aligned-trend, pullback-state, choppy, and
  range-expanding.
- Flow filters: all, flow-confirmed, flow-contrarian, and flow-neutral.
- Target raw signals: 1, 3, and 5 per day.
- Families: multi-horizon trend-follow, trend-pullback resume,
  state-transition breakout, trend-exhaustion fade, choppy mean reversion,
  range-expansion follow, and flow-confirmed momentum.

Costs use 0.0432% taker fee per side plus 0.0150% slippage/spread per side,
for 0.001164 round-trip cost. Cost stress tests 1.00x, 1.25x, 1.50x, and 2.00x
cost multipliers.

## Results

Full pre-May grid:

- Evaluated rows: 40,320.
- Positive pre-May rows: 5,402.
- Positive annual-target rows: 50.
- Loose rows: 135.
- Strict rows: 0.
- Selected rows: 135 loose rows.

The top selected loose pre-May row is:

- Symbol: ETHUSDT.
- Family: multi-horizon trend-follow.
- Template: multi-horizon trend-follow.
- State window: 384 bars.
- Hold: 32 bars.
- Session: US.
- State filter: all.
- Flow filter: flow-confirmed.
- Target signals per day: 1.
- Trades: 155.
- Active months: 28.
- Losing months: 7.
- Annual losses: 2024: 3, 2025: 2, 2026 Jan-Apr: 2.
- Pre-May net return: +1.269778.
- Max drawdown: -0.091575.
- Best-month share: 0.138924.
- Cost-stress survival: 4/4.

This row is active and cost-resilient, but remains loose rather than strict
because it misses annual losing-month caps. The selected loose set is dominated
by ETHUSDT trend-follow, flow-momentum, and range-expansion rows. BTCUSDT
contributes some flow-momentum and range-expansion loose diagnostics, but no
BTCUSDT row is strict.

May 2026 benchmark after fixed loose pre-May selection:

- May-positive selected rows: 17.
- May-negative selected rows: 118.
- May-flat selected rows: 0.
- Best May net return: +0.030352.
- Worst May net return: -0.072618.
- Median May net return: -0.021058.

## Decision

The multi-horizon trend-state family is rejected as currently configured. It
finds many positive active pre-May diagnostics, but no strict pre-May row. The
fixed loose selection fails May 2026 sharply, with 118 negative rows versus 17
positive rows and a materially negative median May return.

Useful follow-up context: ETHUSDT trend-follow rows around a 384-bar state
window and 32-bar hold are the strongest pre-May diagnostics, but their annual
loss profile does not satisfy the requested month-to-month stability target,
and May invalidates the selected set. Future work should not promote them
directly; any new packet would need pre-May-only stability filters or a
different exit model before a fresh May benchmark.

## Artifacts

- `data/research/wpr106_132_multi_horizon_trend_state_search/wpr106_132_multi_horizon_trend_state_summary.json`
- `data/research/wpr106_132_multi_horizon_trend_state_search/pre_may/multi_horizon_trend_state_ranking.parquet`
- `data/research/wpr106_132_multi_horizon_trend_state_search/pre_may/multi_horizon_trend_state_top2000.csv`
- `data/research/wpr106_132_multi_horizon_trend_state_search/pre_may/multi_horizon_trend_state_monthly_returns.parquet`
- `data/research/wpr106_132_multi_horizon_trend_state_search/pre_may/family_summary.parquet`
- `data/research/wpr106_132_multi_horizon_trend_state_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_132_multi_horizon_trend_state_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_132_multi_horizon_trend_state_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_132_multi_horizon_trend_state_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_132_multi_horizon_trend_state_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_132_multi_horizon_trend_state_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_132_multi_horizon_trend_state_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_132_multi_horizon_trend_state_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_132_multi_horizon_trend_state_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_132_multi_horizon_trend_state_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
