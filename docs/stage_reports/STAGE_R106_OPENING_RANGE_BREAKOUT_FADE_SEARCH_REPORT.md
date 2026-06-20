# Stage R106 Opening Range Breakout Fade Search Report

Date: 2026-06-11
Packet: WPR106-129
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of all opening-range length, threshold, filter, hold,
ranking, and selection decisions. May was replayed only after fixed pre-May
loose rows were selected.

## Method

The runner
`data/research/wpr106_129_opening_range_breakout_fade_search/scripts/run_wpr106_129_opening_range_breakout_fade_search.py`
uses WPR106-126 source-context loading over WPR106-96 public-archive BTCUSDT
and ETHUSDT bars plus 15m aggTrade-flow aggregation.

Each symbol has 84,672 15m bars from 2024-01-01 through 2026-05-31. Signals
use completed 15m bars and enter on the next 15m open. Pre-May trades are
required to exit before 2026-05-01.

The grid covers:

- Session anchors: Asia, EU, and US.
- Opening-range lengths: 4, 8, and 16 completed 15m bars.
- Fixed holds: 4, 8, 16, and 32 bars.
- Volatility/volume filters: all, quiet-to-normal, high-volume, and high-range.
- Flow filters: all, flow-confirmed, flow-contrarian, and flow-neutral.
- Target raw signals: 1, 3, and 5 per day.
- Families: opening-range breakout follow, failed-breakout fade, retest
  continuation, inside-range fade, and volume-flow impulse.

Costs use 0.0432% taker fee per side plus 0.0150% slippage/spread per side,
for 0.001164 round-trip cost. Cost stress tests 1.00x, 1.25x, 1.50x, and 2.00x
cost multipliers.

## Results

Full pre-May grid:

- Evaluated rows: 17,280.
- Positive pre-May rows: 2,078.
- Positive annual-target rows: 96.
- Loose rows: 20.
- Strict rows: 0.
- Selected rows: 20 loose rows.

The top pre-May row is an ETHUSDT US-session 4-bar opening-range volume-flow
impulse row with a 32-bar hold, all volatility, flow-neutral filter, and 5
target signals per day. It records +1.038698 pre-May net return, 366 trades,
28 active months, 7 losing months, max drawdown -0.183888, full cost-stress
survival, and best-month share 0.122602. It fails annual stability with 3
losing months in 2024 and 4 in 2025.

Selected loose rows:

- ETHUSDT opening-range volume-flow impulse: 7 rows.
- ETHUSDT opening-range breakout: 7 rows.
- ETHUSDT opening-range retest-continuation: 3 rows.
- BTCUSDT opening-range volume-flow impulse: 2 rows.
- BTCUSDT opening-range breakout: 1 row.

The selected rows concentrate in ETHUSDT US 4-bar opening-range behavior and
BTCUSDT/ETHUSDT EU variants. They are active enough for diagnostics, but they
do not meet the requested month-to-month stability profile.

Annual-target diagnostics:

- Positive annual-target rows: 96.
- They are too sparse for the requested active profile, maxing at 29 trades
  and 15 active months.
- The leading annual-target rows are BTCUSDT Asia failed-breakout fades with
  29 trades, 15 active months, 5 losing months, and +0.064663 pre-May return.

May 2026 benchmark after fixed pre-May selection:

- May-positive selected rows: 0.
- May-negative selected rows: 20.
- May-flat selected rows: 0.
- Best May return: -0.004720.
- Worst May return: -0.044803.
- Median May return: -0.024827.

The best May row is a BTCUSDT EU 8-bar opening-range breakout row; it still
lost -0.004720 in May. The worst May rows are ETHUSDT US 4-bar high-range
volume-flow impulse/breakout rows, each losing about -0.044803.

## Decision

The opening-range breakout/fade family is rejected as currently configured.
It produces active and profitable pre-May diagnostics, but active selected rows
fail annual stability and May rejects every selected row. The sparse
annual-target diagnostics are not active enough to satisfy the requested trade
profile.

Useful follow-up context: ETHUSDT US 4-bar opening-range breakout/flow impulse
is productive pre-May but unstable. It should not be defended directly unless a
future packet adds a new causal regime filter or portfolio complement test that
is selected only on pre-May evidence.

## Artifacts

- `data/research/wpr106_129_opening_range_breakout_fade_search/wpr106_129_opening_range_breakout_fade_summary.json`
- `data/research/wpr106_129_opening_range_breakout_fade_search/pre_may/opening_range_ranking.parquet`
- `data/research/wpr106_129_opening_range_breakout_fade_search/pre_may/opening_range_top2000.csv`
- `data/research/wpr106_129_opening_range_breakout_fade_search/pre_may/opening_range_monthly_returns.parquet`
- `data/research/wpr106_129_opening_range_breakout_fade_search/pre_may/family_summary.parquet`
- `data/research/wpr106_129_opening_range_breakout_fade_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_129_opening_range_breakout_fade_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_129_opening_range_breakout_fade_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_129_opening_range_breakout_fade_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_129_opening_range_breakout_fade_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_129_opening_range_breakout_fade_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_129_opening_range_breakout_fade_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_129_opening_range_breakout_fade_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_129_opening_range_breakout_fade_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_129_opening_range_breakout_fade_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
