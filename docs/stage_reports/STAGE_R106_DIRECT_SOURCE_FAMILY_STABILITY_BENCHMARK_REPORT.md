# Stage R106 Direct Source Family Stability Benchmark Report

Date: 2026-06-12
Packet: WPR106-144
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

All source-row deduplication, source scoring, fixed group construction, member
selection, daily-cap choice, ranking, and selected-row fixation used only
2024-01-01 through 2026-04-30 artifacts. May 2026 was replayed only after the
fixed pre-May selected rows were written.

## Method

The runner
`data/research/wpr106_144_direct_source_family_stability_benchmark/scripts/run_wpr106_144_direct_source_family_stability_benchmark.py`
imports the WPR106-141 artifact-local loader and portfolio replay accounting.
It removes the monthly-rotation layer entirely.

The packet evaluates:

- individual deduplicated source rows with daily caps of 1, 3, and 5 accepted
  trades/day;
- fixed equal-sleeve source-family portfolios grouped by packet, family,
  packet-family, symbol, and packet-symbol;
- fixed portfolios with member counts 3, 5, and 8, selected by pre-May source
  stability only;
- same-symbol overlap skipping and embedded source trade costs for every
  replay.

Strict and loose pre-May gates require positive net return, monthly activity,
bounded losing months by year, active 0.2-5 trades/day behavior, drawdown
control, best-month concentration control, and cost-stress survival. May was
not used for any ranking or selection.

## Results

Deduplication:

- Source rows before dedup: 659.
- Source rows after dedup: 518.
- Duplicate-behavior rows removed: 141.

Pre-May search:

- Individual source rows evaluated: 1,554.
- Fixed source-family portfolio rows evaluated: 627.
- Total evaluated rows: 2,181.
- Positive pre-May rows: 2,170.
- Loose pre-May rows: 1,362.
- Strict pre-May rows: 422.
- Fixed selected strict rows: 120.
- Selected individual source rows: 92.
- Selected fixed source-family portfolios: 28.

May 2026 benchmark:

- May-positive selected rows: 30.
- May-negative selected rows: 90.
- Best May net return: +0.015157.
- Worst May net return: -0.118374.
- Median May net return: -0.002191.
- Individual source rows: 21 positive of 92, median -0.002191.
- Fixed source-family portfolios: 9 positive of 28, median -0.000761.

The broad direct selected set therefore fails May as a family. The fixed top
120 strict rows were not stable enough out of sample despite strong pre-May
profiles.

## Narrow Leads

The packet did surface narrow research-only follow-up leads.

The strongest May-positive direct row was selection rank 17:

- Benchmark ID: `directsrc-4c8749fc185c77cd`.
- Source: WPR106-137 `vetoensemble-0984617d185c319b`.
- Family string:
  `cross_symbol_relative_strength|volatility_quiet_trend_pullback|cross_symbol_flow_led_momentum`.
- Symbol string: `ETHUSDT|ETHUSDT|ETHUSDT`.
- Max accepted trades/day: 1.
- Pre-May trades: 342.
- Active days: 342.
- Trades per active day: 1.000000.
- Active months: 26.
- Losing months: 2.
- Annual losing months: 2024: 1, 2025: 1, 2026 Jan-Apr: 0.
- Pre-May net return: +0.669507.
- Max drawdown: -0.045469.
- Best-month share: 0.148607.
- Daily Sortino: 0.453419.
- May trades: 17.
- May net return: +0.015157.
- May max drawdown: -0.011423.
- May cost-stress survival: 4/4.

Another WPR106-137 direct row, `vetoensemble-2b025e21f7235d09`, appeared twice
under daily caps 3 and 5 with identical pre-May and May behavior:

- Pre-May trades: 404.
- Active months: 26.
- Losing months: 2.
- Pre-May net return: +0.728679.
- Max drawdown: -0.053935.
- May trades: 22.
- May net return: +0.009265.

The highest-ranked selected source, WPR106-135
`microportfolio-3ef6884ef23c9202`, was highly stable pre-May with 28 active
months and only 1 losing month, but May evidence was thin: 4 trades and
+0.001512. It is a monitoring lead only, not strong validation evidence.

The best fixed family portfolios were WPR106-139 ETHUSDT calendar/session
groups. They had strong pre-May stability and positive May around +0.004416,
but May cost-stress survival was only 0.5, so they are not robust leads.

## Decision

WPR106-144 rejects direct source-family selection as a broad rescue: 90 of 120
fixed strict rows lost in May and the median selected row was negative.

The packet does not reject every underlying strategy row. It identifies
WPR106-137 `vetoensemble-0984617d185c319b` and
`vetoensemble-2b025e21f7235d09` as narrow research-only follow-up leads worth
direct controls. Those controls should test source-member ablation,
cross-symbol-relative-strength removal, KNN-veto dependence, shifted/no-KNN
controls, and additional calendar/cluster sensitivity before any candidate
claim.

No candidate-ready row exists from this packet.

## Artifacts

- `data/research/wpr106_144_direct_source_family_stability_benchmark/wpr106_144_direct_source_family_stability_summary.json`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/dedup_summary.json`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/source_load_metadata.json`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/pre_may/deduped_source_universe.parquet`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/pre_may/individual_source_metrics.parquet`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/pre_may/individual_source_metrics.csv`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/pre_may/individual_source_monthly_returns.parquet`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/pre_may/fixed_family_portfolio_metrics.parquet`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/pre_may/fixed_family_portfolio_metrics.csv`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/pre_may/fixed_family_portfolio_monthly_returns.parquet`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/pre_may/direct_source_family_ranking.parquet`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/pre_may/direct_source_family_top2000.csv`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/pre_may/selected_pre_may.csv`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/may_benchmark/selected_may_benchmark_metrics.csv`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_144_direct_source_family_stability_benchmark/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
