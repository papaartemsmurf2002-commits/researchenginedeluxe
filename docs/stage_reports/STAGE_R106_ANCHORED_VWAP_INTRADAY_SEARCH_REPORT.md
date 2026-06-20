# Stage R106 Anchored VWAP Intraday Search Report

Date: 2026-06-11
Packet: WPR106-128
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of all feature, threshold, filter, hold, ranking, and
selection decisions. May was replayed only after fixed pre-May loose rows were
selected.

## Method

The runner
`data/research/wpr106_128_anchored_vwap_intraday_search/scripts/run_wpr106_128_anchored_vwap_intraday_search.py`
uses WPR106-126 source-context loading over WPR106-96 public-archive BTCUSDT
and ETHUSDT bars plus 15m aggTrade-flow aggregation.

Each symbol has 84,672 15m bars from 2024-01-01 through 2026-05-31. Signals
use completed 15m bars and enter on the next 15m open. Pre-May trades are
required to exit before 2026-05-01.

The grid covers:

- VWAP feature windows: 96 and 384 bars.
- Fixed holds: 4, 8, 16, and 32 bars.
- Sessions: all, Asia, EU, and US.
- Volatility/volume filters: all, quiet-to-normal, high-volume, and high-range.
- Flow filters: all, flow-confirmed, flow-contrarian, and flow-neutral.
- Target raw signals: 1, 3, and 5 per day.
- Families: anchored VWAP reversion, displacement momentum, trend pullback,
  range-extreme VWAP fade, and volume-flow impulse.

Costs use 0.0432% taker fee per side plus 0.0150% slippage/spread per side,
for 0.001164 round-trip cost. Cost stress tests 1.00x, 1.25x, 1.50x, and 2.00x
cost multipliers.

## Results

Full pre-May grid:

- Evaluated rows: 15,360.
- Positive pre-May rows: 1,733.
- Positive annual-target rows: 2.
- Loose rows: 52.
- Strict rows: 0.
- Selected rows: 52 loose rows.

The strongest pre-May rows are ETHUSDT anchored VWAP volume-flow impulse and
VWAP displacement momentum variants. The top row uses a 384-bar VWAP feature
window, 32-bar hold, all-session high-range filter, and no flow filter. It
records +1.351260 pre-May net return, 268 trades, 28 active months, 7 losing
months, max drawdown -0.099845, full cost-stress survival, and best-month share
0.118953. It fails annual stability with 5 losing months in 2024, 1 in 2025,
and 1 in 2026 Jan-Apr.

The selected loose rows are active and broad enough to be diagnostically useful
but not stable enough. They are mostly ETHUSDT:

- ETHUSDT volume-flow impulse: 27 selected rows.
- ETHUSDT VWAP displacement momentum: 17 selected rows.
- ETHUSDT trend pullback: 2 selected rows.
- BTCUSDT volume-flow impulse: 4 selected rows.
- BTCUSDT trend pullback: 2 selected rows.

The only two positive annual-target rows are ETHUSDT VWAP displacement momentum
diagnostics with 33 to 46 trades and 18 to 20 active months, so they are too
sparse for the requested active profile.

May 2026 benchmark after fixed pre-May selection:

- May-positive selected rows: 23.
- May-negative selected rows: 28.
- May-flat selected rows: 1.
- Best May return: +0.049556.
- Worst May return: -0.127690.
- Median May return: -0.002863.

The best May row is an ETHUSDT VWAP trend-pullback row using a 96-bar feature
window, 32-bar hold, US session, high-volume filter, and flow-contrarian
filter. It had +0.542137 pre-May return with 137 trades, 28 active months, and
8 losing months, so it was already rejected by pre-May monthly stability.

The worst May row is an ETHUSDT VWAP displacement momentum row using a 384-bar
feature window, 32-bar hold, EU session, high-volume filter, and flow-neutral
filter. It had +0.941765 pre-May return with 508 trades and 28 active months,
but May returned -0.127690, reinforcing the stability rejection.

## Decision

The anchored-VWAP family is rejected as currently configured. It is more
productive than the immediately preceding sweep/wick salvage attempt and
produces many active, cost-positive pre-May rows, but the selected rows fail
the target month-to-month stability profile and May is mixed with a slightly
negative median plus a large negative tail.

Useful follow-up context: ETHUSDT anchored VWAP momentum/flow impulse is worth
keeping in the research knowledge base, but only as a source for future
pre-May-only causal filters or portfolio complement tests. The current fixed
rows are not candidate-ready.

## Artifacts

- `data/research/wpr106_128_anchored_vwap_intraday_search/wpr106_128_anchored_vwap_intraday_summary.json`
- `data/research/wpr106_128_anchored_vwap_intraday_search/pre_may/anchored_vwap_ranking.parquet`
- `data/research/wpr106_128_anchored_vwap_intraday_search/pre_may/anchored_vwap_top2000.csv`
- `data/research/wpr106_128_anchored_vwap_intraday_search/pre_may/anchored_vwap_monthly_returns.parquet`
- `data/research/wpr106_128_anchored_vwap_intraday_search/pre_may/family_summary.parquet`
- `data/research/wpr106_128_anchored_vwap_intraday_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_128_anchored_vwap_intraday_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_128_anchored_vwap_intraday_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_128_anchored_vwap_intraday_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_128_anchored_vwap_intraday_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_128_anchored_vwap_intraday_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_128_anchored_vwap_intraday_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_128_anchored_vwap_intraday_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_128_anchored_vwap_intraday_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_128_anchored_vwap_intraday_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
