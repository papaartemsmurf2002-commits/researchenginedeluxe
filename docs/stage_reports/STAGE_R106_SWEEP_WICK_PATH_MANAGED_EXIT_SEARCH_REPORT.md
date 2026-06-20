# Stage R106 Sweep Wick Path-Managed Exit Search Report

Date: 2026-06-11
Packet: WPR106-127
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of all source-pool, exit-parameter, ranking, and
selection decisions. May was replayed only after fixed pre-May loose rows were
selected.

## Method

The runner
`data/research/wpr106_127_sweep_wick_path_managed_exit_search/scripts/run_wpr106_127_sweep_wick_path_managed_exit_search.py`
imports the WPR106-126 completed-bar feature and signal builder, then replays
WPR106-126 pre-May source rows with path-managed exits.

The source pool is deterministic and pre-May-only:

- 10 WPR106-126 selected loose rows.
- 42 WPR106-126 positive annual-target diagnostics.
- 44 WPR106-126 active positive rows.

The overlay grid covers 18,432 rows across:

- max holds of 4, 8, 16, and 32 bars;
- take-profit levels of 0.4%, 0.6%, 1.0%, and 1.5%;
- stop-loss levels of 0.4%, 0.8%, and 1.2%;
- break-even enabled/disabled;
- trailing disabled or 0.8%.

Signals use completed 15m bars and enter on the next 15m open. Pre-May trades
are required to exit before 2026-05-01. Same-bar TP/SL ambiguity is handled
conservatively with stop-first execution. Break-even and trailing updates
activate only after a completed favorable bar, not intrabar.

Costs use 0.0432% taker fee per side plus 0.0150% slippage/spread per side,
for 0.001164 round-trip cost. Cost stress tests 1.00x, 1.25x, 1.50x, and 2.00x
cost multipliers.

## Results

Pre-May overlay grid:

- Evaluated rows: 18,432.
- Positive pre-May rows: 4,025.
- Positive annual-target rows: 2,585.
- Loose rows: 116.
- Strict rows: 0.
- Selected rows: 116 loose rows.

The annual-target rows remain too sparse for the requested active profile:
the largest annual-target row has 20 trades and 14 active months. The selected
loose rows are active enough, with 68 to 318 trades and 21 to 28 active months,
but none satisfy annual stability caps. They carry 6 to 8 losing months.

The top pre-May row is an ETHUSDT liquidity-sweep reversal overlay from
WPR106-126 source rank 100 with a 32-bar max hold, 1.5% take profit, 1.2% stop
loss, break-even enabled, and no trailing stop. It records +0.433813 pre-May
net return, 313 trades, 28 active months, 8 losing months, 4 losing months in
2024, 4 in 2025, 0 in 2026 Jan-Apr, max drawdown -0.102231, and full
cost-stress survival. It is loose, not strict, because annual stability fails.

May 2026 benchmark after fixed pre-May selection:

- May-positive selected rows: 1.
- May-negative selected rows: 115.
- May-flat selected rows: 0.
- Best May return: +0.007162.
- Worst May return: -0.024864.
- Median May return: -0.013164.

The only May-positive selected row is a BTCUSDT sweep-continuation overlay from
WPR106-126 source rank 2 with a 32-bar max hold, 1.5% take profit, 1.2% stop
loss, no break-even, and no trailing stop. It was already rejected by pre-May
annual stability with 7 losing months and 4 losing months in 2024.

## Decision

The path-managed exit follow-up rejects the WPR106-126 sweep/wick family as
currently salvageable. TP/SL/time-stop overlays increase pre-May positive and
annual-target counts, but annual-stable rows remain sparse, active loose rows
miss annual stability, and May rejects nearly all fixed selected overlays.

Useful follow-up context: the active loose rows are dominated by ETHUSDT
liquidity-sweep reversal sources, while annual-target rows mostly remain sparse
sweep-continuation diagnostics. Future work should broaden the family or add
new pre-May-only causal filters rather than continue defending these exact
rows.

## Artifacts

- `data/research/wpr106_127_sweep_wick_path_managed_exit_search/wpr106_127_sweep_wick_path_managed_exit_summary.json`
- `data/research/wpr106_127_sweep_wick_path_managed_exit_search/pre_may/source_pool.parquet`
- `data/research/wpr106_127_sweep_wick_path_managed_exit_search/pre_may/path_exit_ranking.parquet`
- `data/research/wpr106_127_sweep_wick_path_managed_exit_search/pre_may/path_exit_top2000.csv`
- `data/research/wpr106_127_sweep_wick_path_managed_exit_search/pre_may/path_exit_monthly_returns.parquet`
- `data/research/wpr106_127_sweep_wick_path_managed_exit_search/pre_may/family_summary.parquet`
- `data/research/wpr106_127_sweep_wick_path_managed_exit_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_127_sweep_wick_path_managed_exit_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_127_sweep_wick_path_managed_exit_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_127_sweep_wick_path_managed_exit_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_127_sweep_wick_path_managed_exit_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_127_sweep_wick_path_managed_exit_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_127_sweep_wick_path_managed_exit_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_127_sweep_wick_path_managed_exit_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_127_sweep_wick_path_managed_exit_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_127_sweep_wick_path_managed_exit_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
