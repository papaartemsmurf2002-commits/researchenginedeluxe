# Stage R106 Cross-Symbol Lead-Lag Search Report

Date: 2026-06-11
Packet: WPR106-133
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
`data/research/wpr106_133_cross_symbol_lead_lag_search/scripts/run_wpr106_133_cross_symbol_lead_lag_search.py`
uses WPR106-126 source-context loading over WPR106-96 public-archive BTCUSDT
and ETHUSDT bars plus 15m aggTrade-flow aggregation.

Each symbol has 84,672 15m bars from 2024-01-01 through 2026-05-31. BTCUSDT
and ETHUSDT contexts were required to be timestamp-aligned before any
cross-symbol feature construction. Signals use completed 15m bars and enter on
the target symbol's next 15m open. Pre-May trades are required to exit before
2026-05-01.

The grid covers:

- Pair directions: BTCUSDT->ETHUSDT and ETHUSDT->BTCUSDT.
- Lead-lag feature windows: 96, 384, and 1,536 bars.
- Lag choices: 1 and 4 completed 15m bars.
- Fixed holds: 4, 8, 16, and 32 bars.
- Sessions: all, Asia, EU, and US.
- Relation filters: all, high-correlation, leader-impulse, and
  relative-divergence.
- Flow filters: all, leader-flow-confirmed, target-flow-confirmed, and
  flow-neutral.
- Target raw signals: 1, 3, and 5 per day.
- Families: leader momentum spillover, lagged convergence, relative-strength
  continuation, beta-residual reversion, flow-led momentum, and
  correlation-break follow.

Costs use 0.0432% taker fee per side plus 0.0150% slippage/spread per side,
for 0.001164 round-trip cost. Cost stress tests 1.00x, 1.25x, 1.50x, and 2.00x
cost multipliers.

## Results

Full pre-May grid:

- Evaluated rows: 41,472.
- Positive pre-May rows: 4,103.
- Positive annual-target rows: 0.
- Loose rows: 59.
- Strict rows: 0.
- Selected rows: 59 loose rows.

The top selected loose pre-May row is:

- Pair direction: BTCUSDT->ETHUSDT.
- Target symbol: ETHUSDT.
- Family: cross-symbol relative strength.
- Template: relative-strength continuation.
- Lead-lag window: 96 bars.
- Lag: 4 bars.
- Hold: 32 bars.
- Session: all.
- Relation filter: all.
- Flow filter: flow-neutral.
- Target signals per day: 5.
- Trades: 623.
- Active months: 28.
- Losing months: 7.
- Annual losses: 2024: 4, 2025: 2, 2026 Jan-Apr: 1.
- Pre-May net return: +1.384103.
- Max drawdown: -0.184168.
- Best-month share: 0.128455.
- Cost-stress survival: 4/4.

The loose set is concentrated in BTCUSDT->ETHUSDT rows: 54 of 59 selected rows
trade ETHUSDT from BTCUSDT leader context. Relative-strength continuation and
leader-momentum spillover dominate the selected diagnostics. ETHUSDT->BTCUSDT
contributes only five loose rows and no annual-target rows.

May 2026 benchmark after fixed loose pre-May selection:

- May-positive selected rows: 6.
- May-negative selected rows: 53.
- May-flat selected rows: 0.
- Best May net return: +0.065272.
- Worst May net return: -0.132690.
- Median May net return: -0.034385.

## Decision

The cross-symbol lead-lag family is rejected as currently configured. It found
active positive pre-May diagnostics, but no row met the annual stability target
and no strict pre-May row existed. The fixed loose selection failed May 2026
sharply, with 53 negative rows versus 6 positive rows and a negative median May
return.

Useful follow-up context: BTCUSDT->ETHUSDT relative-strength continuation is
the most productive pre-May diagnostic and includes the best May-positive row,
but the top pre-May variants fail annual stability and the fixed selected set
is not robust in May. Future work should not promote these rows directly; any
follow-up would need pre-May-only stability filters, de-duplication, or a
different exit/portfolio design before another May benchmark.

## Artifacts

- `data/research/wpr106_133_cross_symbol_lead_lag_search/wpr106_133_cross_symbol_lead_lag_summary.json`
- `data/research/wpr106_133_cross_symbol_lead_lag_search/pre_may/cross_symbol_lead_lag_ranking.parquet`
- `data/research/wpr106_133_cross_symbol_lead_lag_search/pre_may/cross_symbol_lead_lag_top2000.csv`
- `data/research/wpr106_133_cross_symbol_lead_lag_search/pre_may/cross_symbol_lead_lag_monthly_returns.parquet`
- `data/research/wpr106_133_cross_symbol_lead_lag_search/pre_may/family_summary.parquet`
- `data/research/wpr106_133_cross_symbol_lead_lag_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_133_cross_symbol_lead_lag_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_133_cross_symbol_lead_lag_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_133_cross_symbol_lead_lag_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_133_cross_symbol_lead_lag_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_133_cross_symbol_lead_lag_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_133_cross_symbol_lead_lag_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_133_cross_symbol_lead_lag_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_133_cross_symbol_lead_lag_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_133_cross_symbol_lead_lag_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
