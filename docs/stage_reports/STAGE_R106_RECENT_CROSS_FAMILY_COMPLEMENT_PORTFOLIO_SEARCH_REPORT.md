# Stage R106 Recent Cross-Family Complement Portfolio Search Report

Date: 2026-06-12
Packet: WPR106-156
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of source scoring, source behavior de-duplication,
portfolio construction, pre-May portfolio behavior de-duplication, ranking, and
selection. May was replayed only after fixed strict pre-May rows were selected.

## Method

The runner
`data/research/wpr106_156_recent_cross_family_complement_portfolio_search/scripts/run_wpr106_156_recent_cross_family_complement_portfolio_search.py`
loads fixed selected artifacts from WPR106-151 through WPR106-155:

- WPR106-151 causal multi-day level retest.
- WPR106-152 level-source KNN trade filter.
- WPR106-153 intrabar order-flow event search.
- WPR106-154 cross-symbol intrabar flow transfer.
- WPR106-155 causal Lorentzian regime KNN.

The source pool uses only 2024-01-01 through 2026-04-30 evidence. Source rows
are behavior-de-duplicated by pre-May accepted trade path
`symbol/entry_time/exit_time/side`; the best representative per behavior hash
is retained.

The search constructs equal-sleeve portfolios from high-quality source seeds
using four deterministic pre-May-only modes:

- `quality`
- `loss_complement`
- `low_corr`
- `packet_diverse`

Member counts are 2, 3, 5, and 8. Accepted-trade daily caps are 1, 3, and 5.
Portfolio replay applies embedded source net/gross returns divided by sleeve
count, same-symbol overlap skipping, global daily caps, monthly stability
metrics, and cost stress. Raw portfolios are then de-duplicated again by their
pre-May accepted portfolio trade path before selection, so duplicated cap
variants do not dominate the May benchmark.

Compute used deterministic pandas/numpy artifact replay and cached source
trade frames. No CUDA path was used, and no speedup was claimed.

## Results

Source and raw search:

- Loaded source rows: 401.
- Behavior-deduplicated source rows: 153.
- Generated raw portfolios: 2,154.
- Pre-May portfolio-behavior-deduplicated rows: 1,852.
- Positive pre-May rows after portfolio de-duplication: 1,852.
- Positive annual-target rows: 273.
- Loose rows: 1,563.
- Strict rows: 273.
- Selected rows: 100 strict rows.

Selected pre-May rows:

- Net-return range: +0.550936 to +0.864151.
- Mean net return: +0.639505.
- Trade-count range: 204 to 1,881.
- Active-month range: 26 to 28.
- Losing-month range: 2 to 5.
- Mean losing months: 3.64.
- Max-drawdown range: -0.159235 to -0.031134.
- Cost-stress survival: selected rows survive 4/4 cost multipliers.

The top selected pre-May portfolio is:

- Portfolio: `recentpf-a90a13de05eec9e9`.
- Construction mode: `quality`.
- Member count: 2.
- Accepted-trade daily cap: 3.
- Members: `WPR106-152:levelknn-ac064ca5bef3994a` and
  `WPR106-153:intrabarof-423ffe9e90d52a36`.
- Trades: 564.
- Active months: 28.
- Losing months: 5.
- Annual losses: 2024: 2, 2025: 2, 2026 Jan-Apr: 1.
- Pre-May net return: +0.864151.
- Max drawdown: -0.103308.
- Best-month share: 0.126470.
- Cost-stress survival: 4/4.

The strict rows are useful as diagnostics, but the strongest rows remain
clustered around WPR106-152 level-KNN overlays plus WPR106-153 intrabar sources.
Pre-May portfolio behavior de-duplication removed cap duplicates, but it did
not remove the shared-component concentration.

May 2026 benchmark after fixed strict pre-May selection:

- May-positive selected rows: 0.
- May-negative selected rows: 100.
- May-flat selected rows: 0.
- Best May return: -0.002595.
- Worst May return: -0.045187.
- Median May return: -0.019671.
- May trade-count range: 6 to 80.
- May mean monthly return across selected rows: -0.022830.

The least-bad May row is
`recentpf-e953971e8a8ae5bf`, a `packet_diverse` 5-member portfolio capped at 3
trades/day, with 57 May trades and -0.002595 May net return. It is still
negative and therefore not a holdout pass.

## Decision

The recent cross-family complement portfolio search is rejected as
candidate-ready. It finds many attractive strict pre-May rows under the target
2024-forward stability metrics, but every selected strict row loses in the
fully held-out May 2026 benchmark. The result argues against defending the
recent WPR106-151 through WPR106-155 rejected/near-miss families by simple
equal-sleeve complement portfolios.

Useful follow-up context: the failure is not caused by low trade activity.
Selected rows actively trade at capped rates and remain within the allowed
1-to-5/day research target. The problem is holdout fragility and component
concentration. A future packet should either test materially different source
families or apply stricter pre-May-only source-diversity/component-exposure
controls before May benchmarking; May should still remain benchmark-only.

## Artifacts

- `data/research/wpr106_156_recent_cross_family_complement_portfolio_search/wpr106_156_recent_cross_family_complement_portfolio_summary.json`
- `data/research/wpr106_156_recent_cross_family_complement_portfolio_search/pre_may/behavior_dedup_source_pool.parquet`
- `data/research/wpr106_156_recent_cross_family_complement_portfolio_search/pre_may/source_monthly_return_matrix.parquet`
- `data/research/wpr106_156_recent_cross_family_complement_portfolio_search/pre_may/generated_portfolio_definitions.parquet`
- `data/research/wpr106_156_recent_cross_family_complement_portfolio_search/pre_may/recent_cross_family_portfolio_raw_ranking.parquet`
- `data/research/wpr106_156_recent_cross_family_complement_portfolio_search/pre_may/recent_cross_family_portfolio_ranking.parquet`
- `data/research/wpr106_156_recent_cross_family_complement_portfolio_search/pre_may/recent_cross_family_portfolio_monthly_returns.parquet`
- `data/research/wpr106_156_recent_cross_family_complement_portfolio_search/pre_may/recent_cross_family_portfolio_daily_returns.parquet`
- `data/research/wpr106_156_recent_cross_family_complement_portfolio_search/pre_may/family_summary.parquet`
- `data/research/wpr106_156_recent_cross_family_complement_portfolio_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_156_recent_cross_family_complement_portfolio_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_156_recent_cross_family_complement_portfolio_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_156_recent_cross_family_complement_portfolio_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_156_recent_cross_family_complement_portfolio_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_156_recent_cross_family_complement_portfolio_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_156_recent_cross_family_complement_portfolio_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_156_recent_cross_family_complement_portfolio_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_156_recent_cross_family_complement_portfolio_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_156_recent_cross_family_complement_portfolio_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
