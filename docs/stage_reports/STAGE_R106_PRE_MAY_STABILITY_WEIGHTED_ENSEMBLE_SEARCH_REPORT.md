# Stage R106 Pre-May Stability Weighted Ensemble Search Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-104-pre-may-stability-weighted-ensemble-search.md`
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It uses
2024-01-01 through 2026-04-30 for optimization, ranking, filtering, weighting,
and selection. May 2026 is joined only after fixed pre-May weighted rows are
selected, and only as a benchmark holdout. No calendar-month selected filter,
candidate pack, paper/live artifact, order placement, sizing change,
runtime-mode change, live configuration write, CUDA speedup claim, or promotion
claim is made.

## Method

The runner starts from existing WPR106-102 evidence: the 120 positive
WPR106-95/WPR106-102 sleeves, their pre-May sleeve returns/trades, and the
WPR106-102 top-1000 equal-weight portfolio proposals. It does not introduce a
new source artifact, a live adapter, a live runtime path, or May feedback.

For each proposal member set, the runner evaluates bounded deterministic
non-equal weights: equal-weight baselines, formula weights based on pre-May
loss/volatility/positive-month complements, and small integer grids using
weights 1, 2, and 3. Weights are positive and normalized within the fixed
member set. This is intentionally not an unconstrained continuous optimizer.

The pre-May scoring keeps active 1-to-5 trades per active day acceptable when
overlap, cost stress, split exposure, concentration, diversity, duplicate
behavior, and annual month-stability controls pass. May artifacts from
WPR106-97, WPR106-102, and WPR106-103 are joined only after the 40 fixed
pre-May rows are selected. No selected row required a new supplemental May
replay; the supplemental WPR106-104 May files are present only as empty,
schema-stable outputs.

## Results

The search evaluated 347,110 weighted rows from 1,000 base combo proposals and
120 positive sleeves. It found 16,205 full-year target rows and 603 strict
weighted stability rows. The 40 selected rows are all strict weighted pre-May
rows and all have May benchmark evidence. May was not used for selection.

| Selected Rank | Combo | Pre-May Return | Losing Months | Annual Losses | May Return | May Trades | May Days | Note |
| ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| 1 | `combo104-b91239b7624cf3dd` | +0.509107 | 3 | 2024: 1, 2025: 2, 2026 Jan-Apr: 0 | -0.029783 | 22 | 11 | Best pre-May stability row, but May rejects it. |
| 17 | `combo104-79845898d8cf3c95` | +0.904687 | 4 | 2024: 2, 2025: 2, 2026 Jan-Apr: 0 | +0.013958 | 42 | 26 | Best May-positive selected row; May day balance remains mixed. |
| 22 | `combo104-35b2f9dd99c6dfe4` | +0.890966 | 4 | 2024: 2, 2025: 2, 2026 Jan-Apr: 0 | +0.013958 | 42 | 26 | Same May benchmark as rank 17 with a nearby member set. |
| 28 | `combo104-e9d45313512bc0ae` | +0.849481 | 4 | 2024: 2, 2025: 2, 2026 Jan-Apr: 0 | +0.004301 | 42 | 26 | Positive but small May benchmark. |
| 27 | `combo104-e63d81a529759513` | +0.867776 | 4 | 2024: 2, 2025: 2, 2026 Jan-Apr: 0 | +0.004301 | 42 | 26 | Positive but small May benchmark. |

Across the 40 selected rows, 4 are May-positive and 36 are May-negative. The
top pre-May row improves the month-stability target to 3 losing months over
2024-01-01 through 2026-04-30, with 561 trades, 302 active days,
1.858 trades per active day, and 0.493 overlap-day share, but its May
benchmark is -0.029783 with only 4 positive days and 7 losing days.

The best May-positive selected rows are still modest: +0.013958 or +0.004301
in May, 42 trades, 26 active days, 14 positive days, and 12 losing days. They
are useful diagnostics, not clean holdout confirmations.

## Interpretation

Constrained weighting improves the pre-May stability profile versus the prior
equal-sleeve defense path: WPR106-104 finds a strict pre-May row with only
3 losing months, while the WPR106-100/102/103 strict lead remained at
5 losing months. That improvement does not transfer cleanly to May. The
strongest stability row is May-negative, and only 4 of 40 selected rows are
May-positive.

This makes bounded weighting useful as a diagnostic and allocation stress test,
but not a candidate-ready lead. The next useful direction is broader than
reweighting this same sleeve library: revisit discarded families, introduce
genuinely new entry/feature/filter/exit logic, or run scoped Lorentzian/KNN
variants under the same pre-May-only selection and May benchmark discipline.

## Artifacts

- `data/research/wpr106_104_pre_may_stability_weighted_ensemble_search/scripts/run_wpr106_104_weighted_ensemble_search.py`
- `data/research/wpr106_104_pre_may_stability_weighted_ensemble_search/pre_may/wpr106_104_base_combo_proposals.csv`
- `data/research/wpr106_104_pre_may_stability_weighted_ensemble_search/pre_may/wpr106_104_weighted_ensemble_ranking.parquet`
- `data/research/wpr106_104_pre_may_stability_weighted_ensemble_search/pre_may/wpr106_104_weighted_ensemble_top1000.csv`
- `data/research/wpr106_104_pre_may_stability_weighted_ensemble_search/pre_may/wpr106_104_selected_pre_may_leads.csv`
- `data/research/wpr106_104_pre_may_stability_weighted_ensemble_search/pre_may/wpr106_104_selected_monthly_returns.csv`
- `data/research/wpr106_104_pre_may_stability_weighted_ensemble_search/may_benchmark/wpr106_104_selected_may_benchmark.csv`
- `data/research/wpr106_104_pre_may_stability_weighted_ensemble_search/may_benchmark/wpr106_104_selected_may_daily_returns.csv`
- `data/research/wpr106_104_pre_may_stability_weighted_ensemble_search/may_benchmark/wpr106_104_selected_may_member_contributions.csv`
- `data/research/wpr106_104_pre_may_stability_weighted_ensemble_search/may_benchmark/wpr106_104_supplemental_sleeve_may_summary.csv`
- `data/research/wpr106_104_pre_may_stability_weighted_ensemble_search/may_benchmark/wpr106_104_supplemental_all_sleeve_may_trades.parquet`
- `data/research/wpr106_104_pre_may_stability_weighted_ensemble_search/may_benchmark/wpr106_104_supplemental_all_sleeve_may_signals.parquet`
- `data/research/wpr106_104_pre_may_stability_weighted_ensemble_search/wpr106_104_weighted_ensemble_summary.json`

## Validation

- `python -m compileall -q data/research/wpr106_104_pre_may_stability_weighted_ensemble_search/scripts`: passed.
- `python -m compileall -q src/tradingbotsuite`: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`: 460 passed.
