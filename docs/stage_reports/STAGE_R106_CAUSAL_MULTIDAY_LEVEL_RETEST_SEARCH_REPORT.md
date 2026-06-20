# Stage R106 Causal Multi-Day Level Retest Search Report

Date: 2026-06-12
Packet: WPR106-151
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of all feature, threshold, filter, hold, daily-cap,
loss-throttle, ranking, and selection decisions. May was replayed only after
the fixed strict pre-May row was selected.

## Method

The runner
`data/research/wpr106_151_causal_multiday_level_retest_search/scripts/run_wpr106_151_causal_multiday_level_retest_search.py`
reuses WPR106-126 source loading, period masks, cost accounting, and monthly
stability metrics over WPR106-96 public-archive BTCUSDT/ETHUSDT 15m bars and
15m aggTrade-flow context.

Each symbol has 84,672 15m bars from 2024-01-01 through 2026-05-31. Signals
use completed 15m bars and enter on the next 15m open. Pre-May trades are
required to exit before 2026-05-01.

The grid covers:

- Level scopes: prior completed day, prior completed five-day range, and prior
  completed week.
- Templates: breakout follow, failed-break fade, retest rejection, retest
  momentum, and midline reversion.
- Normalization windows: 96 and 384 bars.
- Fixed holds: 8, 16, and 32 bars.
- Sessions: all and US.
- Range-state filters: all, high-range, and compressed.
- Flow filters: all, flow-confirmed, and flow-contrarian.
- Side modes: both, long-only, and short-only.
- Target raw signals: 1, 3, and 5 per day.
- Accepted-trade daily caps: 1 and 5.
- Loss-throttle modes: none and skip after one prior completed losing month.

Costs use 0.0432% taker fee per side plus 0.0150% slippage/spread per side,
for 0.001164 round-trip cost. Cost stress tests 1.00x, 1.25x, 1.50x, and 2.00x
cost multipliers through the reused WPR106-126 metrics.

## Results

Full pre-May grid:

- Evaluated rows: 113,400.
- Positive pre-May rows: 28,627.
- Positive annual-target rows: 3,850.
- Loose rows: 1,812.
- Strict rows: 1.
- Selected rows: 1 strict row.

The selected strict pre-May row is:

- Candidate: `multilevel-4225b47443d90024`.
- Symbol: BTCUSDT.
- Family/template: multiday level breakout follow / breakout follow.
- Level scope: prior completed day.
- Normalization window: 96 bars.
- Hold: 32 bars.
- Session: US.
- Range-state filter: compressed.
- Flow filter: flow-confirmed.
- Side mode: long-only.
- Target raw signals: 5 per day.
- Accepted-trade daily cap: 1.
- Loss throttle: none.
- Trades: 120.
- Active months: 28.
- Losing months: 4.
- Annual losses: 2024: 1, 2025: 2, 2026 Jan-Apr: 1.
- Pre-May net return: +0.257106.
- Max drawdown: -0.070493.
- Best-month share: 0.175802.
- Cost-stress survival: 4/4.

Broader diagnostics:

- Loose rows have median 108 trades, median 21 active months, median 8 losing
  months, and returns from +0.018236 to +0.966779.
- Positive annual-target rows are mostly sparse: median 14 trades and median 7
  active months.
- The largest loose pre-May returns concentrate in ETHUSDT prior-day breakout
  follow rows, but they miss annual loss caps or total losing-month limits.

May 2026 benchmark after fixed strict pre-May selection:

- May-positive selected rows: 0.
- May-negative selected rows: 1.
- May-flat selected rows: 0.
- May trades: 3.
- May net return: -0.010441.
- May max drawdown: -0.010441.

## Decision

The causal multi-day level retest family is rejected as currently configured.
It found one legitimate strict pre-May diagnostic row, but that row failed the
May 2026 benchmark. The broader loose and annual-target diagnostics remain
useful for research triage, especially prior-day breakout-follow and ETHUSDT
breakout/retest variants, but no candidate-ready, paper-ready, live-ready, or
promotion-ready claim exists.

Useful follow-up context: this packet improves the old prior-day-level evidence
by adding daily caps, side modes, multi-day/weekly levels, retest/failure
variants, and prior-month loss throttles, but the only strict survivor is still
a BTCUSDT prior-day breakout variant and May contradicts it. Future work should
not promote this row directly; it would need new pre-May-only evidence such as
behavior de-duplication, rolling pre-May holdout controls, or a different
source family.

## Artifacts

- `data/research/wpr106_151_causal_multiday_level_retest_search/wpr106_151_causal_multiday_level_retest_summary.json`
- `data/research/wpr106_151_causal_multiday_level_retest_search/pre_may/multiday_level_retest_ranking.parquet`
- `data/research/wpr106_151_causal_multiday_level_retest_search/pre_may/multiday_level_retest_top2000.csv`
- `data/research/wpr106_151_causal_multiday_level_retest_search/pre_may/multiday_level_retest_monthly_returns.parquet`
- `data/research/wpr106_151_causal_multiday_level_retest_search/pre_may/family_summary.parquet`
- `data/research/wpr106_151_causal_multiday_level_retest_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_151_causal_multiday_level_retest_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_151_causal_multiday_level_retest_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_151_causal_multiday_level_retest_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_151_causal_multiday_level_retest_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_151_causal_multiday_level_retest_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_151_causal_multiday_level_retest_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_151_causal_multiday_level_retest_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_151_causal_multiday_level_retest_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_151_causal_multiday_level_retest_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
