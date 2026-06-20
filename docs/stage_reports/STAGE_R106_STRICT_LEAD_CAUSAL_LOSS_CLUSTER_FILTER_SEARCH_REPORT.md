# Stage R106 Strict Lead Causal Loss-Cluster Filter Search Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-101-strict-lead-causal-loss-cluster-filter-search.md`
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It uses
2024-01-01 through 2026-04-30 for optimization and filter selection. May 2026
is joined only after fixed pre-May filter rows are selected, and only as a
benchmark holdout. No calendar-month selected filter, candidate pack,
paper/live artifact, order placement, sizing change, runtime-mode change, live
configuration write, CUDA speedup claim, or promotion claim is made.

## Method

The run starts from the fixed WPR106-100 strict lead
`combo100-8e6136c0927425b1`, preserving its five equal-sleeve accounting model.
The runner evaluates 621 deterministic causal pre-entry filters over side,
regime, volatility bucket, UTC hour group, UTC weekday group, bounded global
pairwise combinations, and member-specific single-dimension filters. Selection
uses only pre-May evidence, active 1-to-5 trades-per-active-day controls,
overlap controls, annual losing-month limits, partial-2026 loss limits,
positive-month concentration, cost-stress proxy, sleeve-balance proxy, and
monthly behavior de-duplication.

## Results

The pre-May ranking produced 621 filter rows, including 51 promising pre-May
filters. The selected behavior-unique set contains 40 rows; 30 were
pre-May-promising. In the May benchmark, 1 selected row was positive, 29 were
negative, and 10 had zero May trades.

The best selected pre-May filter is `filter-212bec7b6e491417`, a member-specific
weekday filter on the WPR106-91 BTC sleeve. It improves pre-May return to
+1.042087 with 890 trades, 28 active months, 1.686 trades per active day,
0.481 overlap-day share, and the same 5 total losing months as the baseline
with annual losses of 2 in 2024, 2 in 2025, and 1 in 2026 Jan-Apr. Its May
benchmark is -0.008109 with 33 trades, 24 active days, 7 positive days, and
17 losing days.

The unfiltered WPR106-100 strict lead appears as selected rank 12. It keeps
+0.969026 pre-May return, 974 trades, 28 active months, 1.758 trades per active
day, 0.507 overlap-day share, 5 total losing months, and annual losses of 2 in
2024, 2 in 2025, and 1 in 2026 Jan-Apr. Its May benchmark remains -0.007165
with 35 trades, 26 active days, 8 positive days, and 18 losing days.

The only selected pre-May-promising row with positive May is
`filter-db75e31526935ed3`, a member-specific short-only filter on the WPR106-94
ETH sleeve. It has +0.749948 pre-May return, 5 total pre-May losing months,
annual losses of 2 in 2024 and 2 in 2025, and a barely positive May benchmark
of +0.000745 with 34 trades, 26 active days, 1.308 trades per active day,
0.308 overlap-day share, 8 positive days, and 18 losing days.

## Interpretation

The causal filters can reshape the WPR106-100 strict lead and slightly improve
some pre-May scores, but they do not reduce the losing-month count below the
strict lead's 5-month profile and do not confirm in May. The best pre-May
filter is worse than the baseline in May, while the only May-positive selected
filter gives up substantial pre-May return and is close to flat in the holdout.
This rejects a scoped single-filter defense of the WPR106-100 strict lead as a
clean holdout lead.

The next useful research direction is broader family-level entry/feature/exit
work rather than more narrow causal filters around the same strict portfolio.
The known loss clusters from WPR106-99/WPR106-100, especially 2024-09,
2024-12, 2025-06, 2025-12, and 2026-04, remain useful diagnostics, but May
2026 must remain out of any tuning loop.

## Artifacts

- `data/research/wpr106_101_strict_lead_causal_loss_cluster_filter_search/scripts/run_wpr106_101_causal_filter_search.py`
- `data/research/wpr106_101_strict_lead_causal_loss_cluster_filter_search/pre_may/wpr106_101_strict_lead_pre_may_trades.parquet`
- `data/research/wpr106_101_strict_lead_causal_loss_cluster_filter_search/pre_may/wpr106_101_causal_filter_ranking.parquet`
- `data/research/wpr106_101_strict_lead_causal_loss_cluster_filter_search/pre_may/wpr106_101_causal_filter_ranking_top1000.csv`
- `data/research/wpr106_101_strict_lead_causal_loss_cluster_filter_search/pre_may/wpr106_101_selected_pre_may_filters.csv`
- `data/research/wpr106_101_strict_lead_causal_loss_cluster_filter_search/pre_may/wpr106_101_selected_filter_monthly_returns.csv`
- `data/research/wpr106_101_strict_lead_causal_loss_cluster_filter_search/may_benchmark/wpr106_101_selected_filter_may_benchmark.csv`
- `data/research/wpr106_101_strict_lead_causal_loss_cluster_filter_search/may_benchmark/wpr106_101_selected_filter_may_daily_returns.csv`
- `data/research/wpr106_101_strict_lead_causal_loss_cluster_filter_search/may_benchmark/wpr106_101_selected_filter_may_member_contributions.csv`
- `data/research/wpr106_101_strict_lead_causal_loss_cluster_filter_search/wpr106_101_causal_filter_summary.json`

## Validation

- `python -m compileall -q src/tradingbotsuite`: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`: 460 passed.
