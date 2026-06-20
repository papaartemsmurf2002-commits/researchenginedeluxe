# WPR106-159 Monthly Dropout Stability Selector

Status: closed
Date: 2026-06-12
Stage: R106 strategy research

## Objective

Run a May-blind stability-first follow-up to WPR106-158 that directly targets
the requested month-to-month profile. The packet reuses the broad WPR106
artifact universe but changes the selector again: it ranks only rows that are
robust to removing their best pre-May months, satisfy annual losing-month
limits, and avoid single-window concentration before May 2026 is replayed.

Optimization and selection use 2024-01-01 through 2026-04-30 only. May 2026 is
fully excluded from stability scoring, dropout scoring, annual loss limits,
ranking, exposure caps, and selection. May 2026 is used only as a fixed
benchmark holdout after selected pre-May rows are fixed.

## Allowed Paths

- `docs/work_packets/WPR106-159-monthly-dropout-stability-selector.md`
- `docs/stage_reports/STAGE_R106_MONTHLY_DROPOUT_STABILITY_SELECTOR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_159_monthly_dropout_stability_selector/**`

## Inputs

- Read-only WPR106-157 and WPR106-158 runners/artifacts under
  `data/research/wpr106_157_broad_artifact_component_exposure_selector/**` and
  `data/research/wpr106_158_nested_pre_may_family_holdout_selector/**`.
- Read-only local WPR106 selected artifact directories consumed by WPR106-157.

## Method

- Reuse the WPR106-157 artifact-universe builder to normalize local selected
  packet artifacts and recompute common pre-May metrics from trade details.
- Compute pre-May monthly stability diagnostics for every behavior-deduped row:
  - 2024, 2025, and 2026 Jan-Apr annual return and losing-month counts;
  - total active, winning, losing, and flat month counts;
  - best-month share and worst-month severity;
  - returns after removing the best one, two, and three pre-May months;
  - rolling three-month and six-month window counts and worst windows;
  - early and late pre-May subperiod returns.
- Select only from pre-May evidence using annual loss caps, dropout robustness,
  rolling-window robustness, cost stress, drawdown limits, active trade-rate
  caps, and strict packet/component/symbol exposure caps.
- Replay the fixed selected set on May 2026 only after pre-May selection.
- Keep outputs research-only, observe-only, and `promotion_ready: false`.

## Validation

- `python -m compileall -q data/research/wpr106_159_monthly_dropout_stability_selector/scripts` -> passed
- `python -m compileall -q src/tradingbotsuite` -> passed
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

## Result

Completed the May-blind monthly dropout stability selector and wrote the stage
report at
`docs/stage_reports/STAGE_R106_MONTHLY_DROPOUT_STABILITY_SELECTOR_REPORT.md`.

The run reused the WPR106-157 artifact universe, included 43 local packet
directories, loaded 2,925 metric rows, 591,571 pre-May trade rows, and 21,216
May benchmark trade rows, and behavior-de-duplicated to 1,915 source rows. It
found 326 monthly-elite rows, 442 dropout-robust rows, and 849
rolling-survivor rows.

The fixed selected set contains 78 `monthly_elite`, 10 `dropout_robust`, and
12 `rolling_survivor` rows. Pre-May metrics are stability-filtered: selected
rows have 85 to 983 trades, 21 to 28 active months, 1 to 9 monthly losing
months, +0.054780 to +2.480657 total net return, and +0.035858 to +1.630755
return after removing the best three pre-May months.

May 2026 rejects the fixed set: 18 rows are positive, 80 are negative, and 2
are flat; best May return is +0.047219, worst is -0.133646, median is
-0.016834, and mean is -0.020599. WPR106-146 cross-symbol relative-strength
trade-veto and WPR106-128 anchored VWAP rows remain small research-only
positive pockets, but the aggregate selector is not candidate-ready or
portfolio-ready.

No candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim was made.

## Exit Criteria

- Write dropout-ranked source rows, selected pre-May rows/trades, May
  benchmark, summary, and stage report artifacts.
- Update the stage ledger with the packet decision.
- Do not write a candidate pack or make paper/live/promotion claims.
