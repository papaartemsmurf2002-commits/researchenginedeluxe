# Stage R106 Split-Balance Repair Replacement Search Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-103-split-balance-repair-replacement-search.md`
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It uses
2024-01-01 through 2026-04-30 for optimization, ranking, filtering,
replacement, and selection. May 2026 is joined only after fixed pre-May rows are
selected, and only as a benchmark holdout. No calendar-month selected filter,
candidate pack, paper/live artifact, order placement, sizing change,
runtime-mode change, live configuration write, CUDA speedup claim, or promotion
claim is made.

## Method

The runner starts from the WPR106-102 broader positive sleeve universe, which
contains 120 WPR106-95 positive-net and positive-expectancy sleeves. It then
builds an exact split-clean replacement pool by requiring each member sleeve to
have `max_single_split_pnl_share <= 0.80`. That leaves 12 sleeves.

All 2-to-6 sleeve combinations over the 12-sleeve pool are evaluated exactly,
for 2,497 pre-May portfolios. The search keeps active 1-to-5 trades per active
day acceptable when overlap, cost, split, and month-stability controls pass.
Ranking favors annual losing-month control, partial-2026 stability, overlap,
cost stress, split balance, behavior uniqueness, and family/symbol/packet
diversity before any May join.

After selecting 40 fixed pre-May rows, the May benchmark join reuses existing
WPR106-97 and WPR106-102 May artifacts where available. One selected missing
sleeve was replayed with the existing WPR106-97 feature frame and original
configuration; the supplemental run completed with `run_status=ok`. May
benchmark outputs are marked benchmark-only and were not used for selection.

## Results

The search evaluated 2,497 portfolios from 12 split-clean sleeves. Three rows
meet the full-year target of no more than two losing months in both 2024 and
2025, but only one row also passes partial-2026 loss controls and every strict
split-clean control.

| Selected Rank | Combo | Pre-May Return | Losing Months | Annual Losses | May Return | May Trades | May Days | Note |
| ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| 1 | `combo103-8e6136c0927425b1` | +0.969026 | 5 | 2024: 2, 2025: 2, 2026 Jan-Apr: 1 | -0.007165 | 35 | 26 | Only strict split-clean row; same lead rejected in WPR106-100/102. |
| 2 | `combo103-e97c0325ebf5749f` | +1.063996 | 6 | 2024: 2, 2025: 2, 2026 Jan-Apr: 2 | -0.024204 | 24 | 18 | Full-year target only; fails partial-2026 loss control. |
| 3 | `combo103-e27e801c309eb660` | +0.944435 | 6 | 2024: 2, 2025: 2, 2026 Jan-Apr: 2 | -0.023214 | 25 | 19 | Full-year target only; fails partial-2026 loss control. |

All 40 selected rows have May benchmarks. Nine selected rows are May-positive
and 31 are May-negative. The best May row is selected rank 30,
`combo103-413f32790600ecca`, with +0.036318 May return, 22 trades, 20 active
days, 8 positive days, and 12 losing days; it has 6 pre-May losing months and
4 losing months in 2024, so it is diagnostic only. The best May-positive row
with 5 pre-May losing months is selected rank 11,
`combo103-781f45d2aeec14cd`, with +0.031402 May return, but it has 4 losing
months in 2024 and fails the annual stability target.

## Interpretation

The WPR106-102 rank 2/3 split-balance repair direction did not produce a clean
replacement lead. Removing maximally split-concentrated members collapses the
4-losing-month May-positive direction back to the older strict five-sleeve
portfolio, and that portfolio remains May-negative. May-positive replacements
exist, but their pre-May annual stability is weaker and does not satisfy the
target profile.

This closes the scoped split-balance repair as a falsified defense path, not as
candidate-ready evidence. The useful next direction is broader than this
family-level replacement: either introduce genuinely new features/filters/exit
logic, or revisit other discarded strategy families with the same pre-May-only
selection and May benchmark discipline.

## Artifacts

- `data/research/wpr106_103_split_balance_repair_replacement_search/scripts/run_wpr106_103_split_balance_repair.py`
- `data/research/wpr106_103_split_balance_repair_replacement_search/pre_may/wpr106_103_split_clean_sleeve_pool.csv`
- `data/research/wpr106_103_split_balance_repair_replacement_search/pre_may/wpr106_103_split_clean_portfolio_ranking.parquet`
- `data/research/wpr106_103_split_balance_repair_replacement_search/pre_may/wpr106_103_split_clean_portfolio_top1000.csv`
- `data/research/wpr106_103_split_balance_repair_replacement_search/pre_may/wpr106_103_selected_pre_may_leads.csv`
- `data/research/wpr106_103_split_balance_repair_replacement_search/pre_may/wpr106_103_selected_monthly_returns.csv`
- `data/research/wpr106_103_split_balance_repair_replacement_search/may_benchmark/wpr106_103_supplemental_sleeve_may_summary.csv`
- `data/research/wpr106_103_split_balance_repair_replacement_search/may_benchmark/wpr106_103_supplemental_all_sleeve_may_trades.parquet`
- `data/research/wpr106_103_split_balance_repair_replacement_search/may_benchmark/wpr106_103_supplemental_all_sleeve_may_signals.parquet`
- `data/research/wpr106_103_split_balance_repair_replacement_search/may_benchmark/wpr106_103_selected_may_benchmark.csv`
- `data/research/wpr106_103_split_balance_repair_replacement_search/may_benchmark/wpr106_103_selected_may_daily_returns.csv`
- `data/research/wpr106_103_split_balance_repair_replacement_search/may_benchmark/wpr106_103_selected_may_member_contributions.csv`
- `data/research/wpr106_103_split_balance_repair_replacement_search/wpr106_103_split_balance_repair_summary.json`

## Validation

- `python -m compileall -q data/research/wpr106_103_split_balance_repair_replacement_search/scripts`: passed.
- `python -m compileall -q src/tradingbotsuite`: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`: 460 passed.
