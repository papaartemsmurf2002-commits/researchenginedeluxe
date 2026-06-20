# Stage R106 Broad Family-Level Portfolio Refresh Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-102-broad-family-level-portfolio-refresh.md`
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It uses
2024-01-01 through 2026-04-30 for optimization, ranking, filtering, and
selection. May 2026 is joined only after fixed pre-May rows are selected, and
only as a benchmark holdout. No calendar-month selected filter, candidate pack,
paper/live artifact, order placement, sizing change, runtime-mode change, live
configuration write, CUDA speedup claim, or promotion claim is made.

## Method

The runner starts from the 120 positive-net and positive-expectancy sleeves in
the WPR106-95 universe, not just the WPR106-100 strict-lead members. It builds
a pre-May-only bounded pool of 75 sleeves using pre-May return, losing-month
count, concentration, cost-stress proxy, split proxy, known loss-cluster
complement return, and packet/symbol/family caps. May availability and May
returns are not used in this selection.

The search evaluates 1,560,763 equal-sleeve portfolios. Sizes 2 through 4 are
exhaustive over the bounded pool; sizes 5 and 6 use deterministic beam
expansion from the top pre-May rows. The accounting is vectorized over monthly
return, monthly trade-count, and active-day trade-count matrices. Active 1-to-5
trades per active day, overlap, annual losing-month caps, 2026 Jan-Apr loss
caps, positive-month concentration, cost stress, split balance, duplicate
candidate/core/monthly behavior controls, and family/symbol/packet diversity
are scored before any May join.

WPR106-97 already had May artifacts for 36 sleeves. WPR106-102 selected rows
needed 18 additional fixed sleeves, so the supplemental May runner replayed
those exact selected sleeves with existing WPR106-97 feature frames and original
backtest configs. All 18 supplemental sleeve runs completed with `ok` status.

## Results

The broad refresh wrote 12,000 ranked rows. Of 1,560,763 evaluated portfolios,
2,578 met the full-year target of no more than two losing months in both 2024
and 2025. Only one row passed every strict control: `combo102-8e6136c0927425b1`,
which is the same WPR106-100 strict portfolio. It has +0.969026 pre-May return,
5 losing months, annual losses of 2 in 2024, 2 in 2025, and 1 in 2026 Jan-Apr,
but its May benchmark remains -0.007165 with 35 trades, 26 active days,
8 positive days, and 18 losing days.

The broader pool found new diagnostic pre-May rows with 4 losing months:

| Rank | Combo | Pre-May Return | Losing Months | Annual Losses | May Return | May Trades | May Days | Note |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| 2 | `combo102-e3da17e53356e870` | +0.802657 | 4 | 2024: 2, 2025: 2, 2026 Jan-Apr: 0 | +0.013312 | 42 | 26 | Fails split-balance proxy only. |
| 3 | `combo102-4fe66028c54cd21c` | +0.784362 | 4 | 2024: 2, 2025: 2, 2026 Jan-Apr: 0 | +0.013312 | 42 | 26 | Fails split-balance proxy only. |
| 4 | `combo102-5435e03ef2bf7b80` | +0.508156 | 4 | 2024: 2, 2025: 2, 2026 Jan-Apr: 0 | -0.002941 | 20 | 13 | Fails split-balance proxy only. |

Ranks 2 and 3 are May-positive, but their May day balance is mixed:
12 positive days and 14 losing days. They fail strict status because at least
one member sleeve has `max_single_split_pnl_share=1.0`, so they cannot be used
as candidate-ready evidence.

Across all 40 fixed selected rows, every row now has a May benchmark after the
supplemental replay. Sixteen rows are May-positive and 24 are May-negative.
The best May row is selected rank 17, `combo102-db38d9e4619991fe`, with
+0.027453 May return, 40 trades, 24 active days, 13 positive days, and
11 losing days; it still has 5 pre-May losing months and fails split balance.

## Interpretation

WPR106-102 does find a more interesting diagnostic family-level direction than
the strict WPR106-100 lead: 4-losing-month rows that benchmark positive in May.
That is not enough for a clean lead. The only strict all-control row remains
the already rejected WPR106-100 portfolio, and the new 4-losing-month rows are
blocked by split-balance evidence. Their May returns are positive but modest
and not day-stable enough to override the split proxy failure.

The useful next research direction is not another defense of the strict lead.
It is a split-balance repair or replacement-member search around the rank 2/3
families, using pre-May-only selection, paired feature/split diagnostics, and
May only as a fixed holdout after selection.

## Artifacts

- `data/research/wpr106_102_broad_family_level_portfolio_refresh/scripts/run_wpr106_102_broad_family_refresh.py`
- `data/research/wpr106_102_broad_family_level_portfolio_refresh/scripts/run_wpr106_102_supplemental_may_backtests.py`
- `data/research/wpr106_102_broad_family_level_portfolio_refresh/pre_may/wpr106_102_full_positive_sleeve_universe.csv`
- `data/research/wpr106_102_broad_family_level_portfolio_refresh/pre_may/wpr106_102_all_positive_sleeve_pre_may_summary.csv`
- `data/research/wpr106_102_broad_family_level_portfolio_refresh/pre_may/wpr106_102_all_positive_sleeve_pre_may_trades.parquet`
- `data/research/wpr106_102_broad_family_level_portfolio_refresh/pre_may/wpr106_102_pre_may_bounded_sleeve_pool.csv`
- `data/research/wpr106_102_broad_family_level_portfolio_refresh/pre_may/wpr106_102_broad_family_portfolio_ranking.parquet`
- `data/research/wpr106_102_broad_family_level_portfolio_refresh/pre_may/wpr106_102_broad_family_portfolio_top1000.csv`
- `data/research/wpr106_102_broad_family_level_portfolio_refresh/pre_may/wpr106_102_selected_pre_may_leads.csv`
- `data/research/wpr106_102_broad_family_level_portfolio_refresh/pre_may/wpr106_102_selected_monthly_returns.csv`
- `data/research/wpr106_102_broad_family_level_portfolio_refresh/may_benchmark/supplemental_sleeve_may_summary.csv`
- `data/research/wpr106_102_broad_family_level_portfolio_refresh/may_benchmark/supplemental_all_sleeve_may_trades.parquet`
- `data/research/wpr106_102_broad_family_level_portfolio_refresh/may_benchmark/wpr106_102_selected_may_benchmark.csv`
- `data/research/wpr106_102_broad_family_level_portfolio_refresh/may_benchmark/wpr106_102_selected_may_daily_returns.csv`
- `data/research/wpr106_102_broad_family_level_portfolio_refresh/may_benchmark/wpr106_102_selected_may_member_contributions.csv`
- `data/research/wpr106_102_broad_family_level_portfolio_refresh/wpr106_102_broad_family_refresh_summary.json`

## Validation

- `python -m compileall -q data/research/wpr106_102_broad_family_level_portfolio_refresh/scripts`: passed.
- `python -m compileall -q src/tradingbotsuite`: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`: 460 passed.
