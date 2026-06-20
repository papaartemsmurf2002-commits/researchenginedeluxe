# Stage R106 Cross-Symbol Intrabar Flow Transfer Search Report

Date: 2026-06-12
Packet: WPR106-154
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of all feature, threshold, transfer-filter, side-mode,
daily-cap, throttle, exit, ranking, and selection decisions. May was replayed
only after fixed loose pre-May rows were selected.

## Method

The runner
`data/research/wpr106_154_cross_symbol_intrabar_flow_transfer_search/scripts/run_wpr106_154_cross_symbol_intrabar_flow_transfer_search.py`
loads WPR106-96 BTCUSDT/ETHUSDT 15m bars and reuses the WPR106-153 1m
aggTrade intrabar feature construction. Each symbol has 84,672 15m bars from
2024-01-01 through 2026-05-31, and the BTCUSDT/ETHUSDT contexts are
timestamp-aligned before cross-symbol evaluation.

Signals use completed 15m bars and enter on the next 15m open. Pre-May trades
are required to exit before 2026-05-01.

The packet builds BTCUSDT -> ETHUSDT and ETHUSDT -> BTCUSDT transfer scores
from leader and target intrabar flow shape:

- leader signed-flow pressure;
- leader late-minute delta and flow flips;
- leader absorption;
- target-versus-leader relative flow gaps;
- synchronized leader/target flow;
- target price divergence from leader flow.

The grid covers:

- Normalization windows: 96 and 384 bars.
- Fixed holds: 4, 8, 16, and 32 bars.
- Sessions: all and US.
- Transfer filters: all, leader flow burst, leader late flow, leader
  absorption, relative dislocation, synchronized flow, and cross divergence.
- Side modes: both, long-only, and short-only.
- Target raw signals: 1, 3, and 5 per day.
- Accepted-trade daily caps: 1, 3, and 5.
- Loss-throttle modes: none and skip after one prior completed losing month.
- Templates: leader-flow follow/fade, leader late-flow transfer, leader
  absorption transfer, relative-pressure follow/reversion, synchronized-flow
  follow, and cross-divergence follow.

Costs use the same research fee/slippage model as recent packets: 0.0432%
taker fee per side plus 0.0150% slippage/spread per side, for 0.001164
round-trip cost. Cost stress tests 1.00x, 1.25x, 1.50x, and 2.00x cost
multipliers through the reused WPR106 monthly metrics.

Compute used numpy/pandas arrays with per-symbol and per-pair feature caches.
The first sequential pandas-heavy path was stopped before producing ranking
evidence after timing out. The completed run used an equivalent array-based
pre-May ranking path and the existing detailed replay helper for selected
rows. No CUDA path was used, and no speedup was claimed.

## Results

Full pre-May grid:

- Evaluated rows: 96,768.
- Positive pre-May rows: 2,288.
- Positive annual-target rows: 9.
- Loose rows: 221.
- Strict rows: 0.
- Selected rows: 100 loose rows.

Selected pre-May rows:

- Net-return range: +0.233163 to +0.880270.
- Trade-count range: 158 to 764.
- Active-month range: 20 to 28.
- Losing-month range: 5 to 8.
- No selected row meets the strict gate.

The strongest annual-target pocket is BTCUSDT-led ETHUSDT synchronized-flow
follow under the cross-divergence transfer filter:

- Candidate: `xflow-c8ddcab5f23edaea`.
- Leader/target: BTCUSDT -> ETHUSDT.
- Template/filter: synchronized-flow follow / cross divergence.
- Normalization window: 96 bars.
- Hold: 16 bars.
- Session: all.
- Side mode: long-only.
- Target raw signals: 1 per day.
- Accepted-trade daily cap: 3.
- Loss throttle: skip after one prior completed losing month.
- Trades: 166.
- Active months: 23.
- Losing months: 5.
- Annual losses: 2024: 2, 2025: 2, 2026 Jan-Apr: 1.
- Pre-May net return: +0.447167.
- Max drawdown: -0.070444.
- Best-month share: 0.251185.
- Cost-stress survival: 4/4.

The 9 positive annual-target rows collapse to two unique trade paths, both from
that same BTCUSDT -> ETHUSDT synchronized-flow/cross-divergence setup. They
miss strict acceptance because active months are 23 rather than the 24-month
floor. No positive annual-target row has at least 24 active months.

May 2026 benchmark after fixed loose pre-May selection:

- May-positive selected rows: 31.
- May-negative selected rows: 53.
- May-flat selected rows: 16.
- Best May return: +0.043733.
- Worst May return: -0.110654.
- Median May return: -0.006258.

The top pre-May row benchmarks 8 May trades and -0.006258 net return. The best
May selected rows are ETHUSDT-led BTCUSDT relative-pressure-follow variants
under leader-absorption filters, but those rows are not the pre-May
annual-target pocket and do not supply a stable candidate-ready family.

## Decision

The cross-symbol intrabar flow transfer family is rejected as candidate-ready.
It improves on WPR106-153 by finding a narrow positive annual-target pocket,
but the pocket is duplicated, misses the active-month floor, and is negative
in the May benchmark. The broader selected set remains May-negative on median
and has too many unstable rows.

Useful follow-up context: the BTCUSDT -> ETHUSDT synchronized-flow /
cross-divergence long setup is a near-miss research lead, not a promotion
lead. Any follow-up should repair activity and May robustness using pre-May
only, preferably with behavior de-duplication, rolling pre-May holdouts, and
transparent controls before another May replay.

## Artifacts

- `data/research/wpr106_154_cross_symbol_intrabar_flow_transfer_search/wpr106_154_cross_symbol_intrabar_flow_transfer_summary.json`
- `data/research/wpr106_154_cross_symbol_intrabar_flow_transfer_search/pre_may/cross_symbol_intrabar_flow_transfer_ranking.parquet`
- `data/research/wpr106_154_cross_symbol_intrabar_flow_transfer_search/pre_may/cross_symbol_intrabar_flow_transfer_top2000.csv`
- `data/research/wpr106_154_cross_symbol_intrabar_flow_transfer_search/pre_may/cross_symbol_intrabar_flow_transfer_monthly_returns.parquet`
- `data/research/wpr106_154_cross_symbol_intrabar_flow_transfer_search/pre_may/family_summary.parquet`
- `data/research/wpr106_154_cross_symbol_intrabar_flow_transfer_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_154_cross_symbol_intrabar_flow_transfer_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_154_cross_symbol_intrabar_flow_transfer_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_154_cross_symbol_intrabar_flow_transfer_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_154_cross_symbol_intrabar_flow_transfer_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_154_cross_symbol_intrabar_flow_transfer_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_154_cross_symbol_intrabar_flow_transfer_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_154_cross_symbol_intrabar_flow_transfer_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_154_cross_symbol_intrabar_flow_transfer_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_154_cross_symbol_intrabar_flow_transfer_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
