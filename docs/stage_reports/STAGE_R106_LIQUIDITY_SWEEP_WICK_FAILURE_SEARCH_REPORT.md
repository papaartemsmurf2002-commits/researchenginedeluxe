# Stage R106 Liquidity Sweep Wick-Failure Search Report

Date: 2026-06-11
Packet: WPR106-126
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of all feature, sweep-window, threshold, filter, exit,
ranking, and selection decisions. May was replayed only after fixed pre-May
loose rows were selected.

## Method

The runner
`data/research/wpr106_126_liquidity_sweep_wick_failure_search/scripts/run_wpr106_126_liquidity_sweep_wick_failure_search.py`
tests completed-bar liquidity sweep and wick-failure patterns over the
WPR106-96 public-archive context:

- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/btcusdt_2024_01_to_2026_05_cycle_dataset.parquet`
- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/ethusdt_2024_01_to_2026_05_cycle_dataset.parquet`
- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/btcusdt_2024_01_to_2026_05_agg_trade_1m.parquet`
- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/ethusdt_2024_01_to_2026_05_agg_trade_1m.parquet`

Each symbol has 84,672 15m bars from 2024-01-01 through 2026-05-31. Signals
use completed 15m bars and enter on the next 15m open. Pre-May trades are
required to exit before 2026-05-01, so late-April signals cannot use May price
path during optimization.

The grid covers:

- Prior sweep windows: 32, 96, and 384 bars.
- Fixed holds: 4, 8, 16, and 32 bars.
- Sessions: all and US.
- Volatility filters: all, high-range, and compressed-before-sweep.
- Flow filters: all, flow-confirmed, and flow-contrarian.
- Target raw signals: 1, 3, and 5 per day.
- Families: liquidity sweep reversal, wick rejection, failed breakout reclaim,
  sweep continuation, and flow-absorbed sweep.

Costs use the same research fee/slippage model as recent packets:
0.0432% taker fee per side plus 0.0150% slippage/spread per side, for
0.001164 round-trip cost. Cost stress tests 1.00x, 1.25x, 1.50x, and 2.00x
cost multipliers.

## Results

Full pre-May grid:

- Evaluated rows: 6,480.
- Positive pre-May rows: 486.
- Positive annual-target rows: 42.
- Loose rows: 10.
- Strict rows: 0.
- Selected rows: 10 loose rows.

Selected pre-May rows:

- Best selected row: BTCUSDT liquidity-sweep reversal, 32-bar sweep window,
  32-bar hold, US high-range flow-confirmed, +0.322023 pre-May, 217 trades,
  28 active months, 7 losing months, annual losses 2024: 2, 2025: 4,
  2026 Jan-Apr: 1, max drawdown -0.234212, 4/4 cost-stress survival.
- Selected row range: +0.025050 to +0.322023 pre-May return, 60 to 330 trades,
  21 to 28 active months, 6 to 8 losing months.
- All selected rows missed at least one annual cap, usually 2025 or 2026
  Jan-Apr.

Annual-target diagnostics:

- Positive annual-target rows: 42.
- They are mostly sweep-continuation rows with flow-contrarian filters.
- They are too sparse for the requested active profile. The leading
  annual-target rows have 1 to 37 trades and at most 14 active months.

May 2026 benchmark after fixed pre-May selection:

- May-positive selected rows: 1.
- May-negative selected rows: 9.
- May-flat selected rows: 0.
- Best May return: +0.008896.
- Worst May return: -0.072570.
- Median May return: -0.012010.

The only May-positive selected row is BTCUSDT sweep continuation with
compressed-before-sweep and flow-contrarian filters. It was already rejected by
pre-May annual stability with six losing months in 2024. The top selected
pre-May row benchmarks -0.009791 in May, and the largest selected May loss is
from an ETHUSDT wick-rejection row at -0.072570.

## Decision

The liquidity-sweep/wick-failure family is rejected as currently configured.
It produces a few active, cost-positive pre-May rows and some sparse
annual-target diagnostics, but it does not satisfy the target month-to-month
stability profile. May mostly contradicts the loose selected set, and the only
May-positive selected row was not pre-May stable enough to be a lead.

Useful follow-up context: sweep-continuation with flow-contrarian filters
creates sparse annual-target rows, while liquidity-sweep reversal creates the
active loose rows. A future packet should not defend these exact rows unless it
introduces new pre-May-only evidence such as a different path exit, a stricter
causal volatility regime, or a broader symbol/venue universe.

## Artifacts

- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/wpr106_126_liquidity_sweep_wick_failure_summary.json`
- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/pre_may/sweep_wick_ranking.parquet`
- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/pre_may/sweep_wick_top2000.csv`
- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/pre_may/sweep_wick_monthly_returns.parquet`
- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/pre_may/family_summary.parquet`
- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/pre_may/selected_pre_may.csv`
- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_126_liquidity_sweep_wick_failure_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.

