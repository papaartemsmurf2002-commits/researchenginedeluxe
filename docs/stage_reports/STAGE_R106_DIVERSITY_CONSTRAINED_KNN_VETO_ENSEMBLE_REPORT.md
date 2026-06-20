# Stage R106 Diversity-Constrained KNN Veto Ensemble Report

Date: 2026-06-12
Packet: WPR106-137
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of overlay-universe choice, ensemble construction,
diversity constraints, daily-cap choice, ranking, and selection. May was used
only after the fixed strict pre-May ensemble selection was complete.

## Method

The runner
`data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/scripts/run_wpr106_137_diversity_constrained_knn_veto_ensemble.py`
tests whether the WPR106-136 KNN trade-veto overlay can survive as a diversified
portfolio component instead of as a concentrated standalone row filter.

Inputs:

- WPR106-136 `knn_trade_veto_ranking.parquet`.
- WPR106-136 `source_pool.parquet`.
- WPR106-136 `source_pool_trades_pre_and_may.parquet`.
- WPR106-136 causal replay helpers.

The runner builds a fixed overlay universe from pre-May WPR106-136 rows only,
then replays those overlays with the WPR106-136 causal rule intact: pre-May
trades use only earlier completed source-trade outcomes, while May uses frozen
pre-May history only. It constructs equal-sleeve ensembles with:

- unique source rows equal to member count;
- at least two source packets;
- at least two source families;
- member counts of 3, 4, 5, 6, and 8;
- portfolio-level same-symbol overlap skipping;
- daily caps of 3 and 5 accepted trades;
- inherited taker plus slippage/spread costs and cost stress.

## Results

Pre-May ensemble screen:

- Overlay-universe rows: 120.
- Unique source rows in overlay universe: 103.
- Unique source packets: 5.
- Unique source families: 16.
- Generated diverse member sets: 6,511.
- Evaluated ensemble rows: 13,022.
- Positive pre-May rows: 13,022.
- Annual-target rows: 3,545.
- Loose pre-May rows: 12,557.
- Strict pre-May rows: 3,531.
- Fixed selected rows: 100 strict rows.

The top selected strict ensemble is:

- Ensemble ID: `vetoensemble-12784788211ae017`.
- Members: WPR106-133 lead-lag, WPR106-131 volatility term-structure,
  WPR106-134 microstructure state.
- Families: cross-symbol relative strength, volatility-expansion follow,
  microstructure volatility-burst follow.
- Symbols: ETHUSDT, ETHUSDT, BTCUSDT.
- Daily cap: 3 trades.
- Trades: 518.
- Active days: 404.
- Trades per active day: 1.282178.
- Active months: 26.
- Losing months: 4.
- Annual losses: 2024: 2, 2025: 2, 2026 Jan-Apr: 0.
- Pre-May net return: +0.866623.
- Max drawdown: -0.067977.
- Sortino daily: 0.476433.
- Best-month share: 0.105048.
- Cost-stress survival: 4/4.

The top-100 strict selection is mostly active three-member ensembles:

- Member-count mix: 91 three-member rows, 8 four-member rows, 1 five-member
  row.
- Daily-cap mix: 50 rows at cap 3 and 50 rows at cap 5.
- Selected member packet exposures: WPR106-133 lead-lag 90, WPR106-132
  trend-state 80, WPR106-134 microstructure 77, WPR106-131 volatility
  term-structure 51, WPR106-130 prior-day 12.
- Selected symbol exposures: 250 ETHUSDT sleeves and 60 BTCUSDT sleeves.

May 2026 benchmark after fixed strict pre-May selection:

- May-positive selected rows: 15.
- May-negative selected rows: 85.
- May-flat selected rows: 0.
- Best May net return: +0.019375.
- Worst May net return: -0.045451.
- Median May net return: -0.015958.
- The top-ranked selected ensemble had 26 May trades over 18 active days and
  returned -0.024805.

## Decision

The diversity-constrained KNN-veto ensemble is rejected as a candidate lead.
It fixes the most obvious WPR106-136 concentration problem at construction time
and produces many strict-looking pre-May rows, but the fixed top-100 strict
selection fails the untouched May 2026 benchmark. The May failure is broad
across the selected set rather than isolated to one row.

Useful follow-up context: the pre-May result says KNN-veto overlays can create
apparently stable active ensembles when optimized over 2024-01-01 through
2026-04-30, but the May distribution is still too negative to treat the family
as robust. Future work should avoid defending this lead unless it introduces a
new pre-May-only stability test that directly targets post-window degradation.

## Artifacts

- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/wpr106_137_diversity_constrained_knn_veto_ensemble_summary.json`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/pre_may/overlay_universe.parquet`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/pre_may/wpr136_source_pool_snapshot.parquet`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/pre_may/overlay_pre_may_replay_metrics.parquet`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/pre_may/overlay_pre_may_trades.parquet`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/pre_may/ensemble_ranking.parquet`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/pre_may/ensemble_top2000.csv`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/pre_may/ensemble_monthly_returns.parquet`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
