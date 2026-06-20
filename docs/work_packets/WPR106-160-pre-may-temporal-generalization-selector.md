# WPR106-160 Pre-May Temporal Generalization Selector

Status: closed
Date: 2026-06-12
Stage: R106 strategy research

## Objective

Run a May-blind follow-up to WPR106-159 that tests temporal generalization
inside the pre-May window. The packet reuses the broad WPR106 artifact
universe but changes the selector: it treats 2024-01 through 2025-12 as the
pre-May search history and requires rows to survive a fixed 2026-01 through
2026-04 validation gate before May 2026 is replayed.

Optimization and selection use 2024-01-01 through 2026-04-30 only. May 2026 is
fully excluded from train scoring, validation scoring, dropout scoring, annual
loss limits, ranking, exposure caps, and selection. May 2026 is used only as a
fixed benchmark holdout after selected pre-May rows are fixed.

## Allowed Paths

- `docs/work_packets/WPR106-160-pre-may-temporal-generalization-selector.md`
- `docs/stage_reports/STAGE_R106_PRE_MAY_TEMPORAL_GENERALIZATION_SELECTOR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_160_pre_may_temporal_generalization_selector/**`

## Inputs

- Read-only WPR106-157 artifact-universe runner and generated artifacts under
  `data/research/wpr106_157_broad_artifact_component_exposure_selector/**`.
- Read-only local WPR106 selected artifact directories consumed by WPR106-157.

## Method

- Reuse the WPR106-157 artifact-universe builder to normalize local selected
  packet artifacts and recompute common pre-May metrics from trade details.
- Compute pre-May temporal diagnostics:
  - search history: 2024-01 through 2025-12;
  - validation gate: 2026-01 through 2026-04;
  - annual losing-month counts for 2024 and 2025;
  - validation losing-month count, worst month, and active month count;
  - 2024-2025 best-month dropout and rolling six-month stability;
  - active trade-rate caps and cost/drawdown filters.
- Select only from pre-May evidence using train/validation consistency,
  annual loss caps, dropout robustness, rolling-window robustness, and strict
  packet/component/symbol exposure caps.
- Replay the fixed selected set on May 2026 only after pre-May selection.
- Keep outputs research-only, observe-only, and `promotion_ready: false`.

## Validation

- `python -m compileall -q data/research/wpr106_160_pre_may_temporal_generalization_selector/scripts` -> passed
- `python -m compileall -q src/tradingbotsuite` -> passed
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

## Result

Completed the May-blind pre-May temporal generalization selector and wrote the
stage report at
`docs/stage_reports/STAGE_R106_PRE_MAY_TEMPORAL_GENERALIZATION_SELECTOR_REPORT.md`.

The run reused the WPR106-157 artifact universe, included 43 local packet
directories, loaded 2,925 metric rows, 591,571 pre-May trade rows, and 21,216
May benchmark trade rows, and behavior-de-duplicated to 1,915 source rows. It
found 321 temporal-elite rows, 475 temporal-robust rows, and 873
validation-survivor rows.

The fixed selected set contains 78 `temporal_elite`, 13 `temporal_robust`, and
9 `validation_survivor` rows. Pre-May metrics are temporally gated: selected
rows have 85 to 985 trades, 21 to 28 active months, +0.048081 to +2.038350
search return over 2024-2025, +0.000792 to +0.531043 validation return over
2026 Jan-Apr, and 0 to 2 validation losing months.

May 2026 rejects the fixed set: 20 rows are positive, 78 are negative, and 2
are flat; best May return is +0.067949, worst is -0.133646, median is
-0.017037, and mean is -0.019105. WPR106-146 cross-symbol relative-strength
trade-veto and WPR106-128 anchored VWAP rows remain small research-only
positive pockets, but the aggregate selector is not candidate-ready or
portfolio-ready.

No candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim was made.

## Exit Criteria

- Write temporal-ranked source rows, selected pre-May rows/trades, May
  benchmark, summary, and stage report artifacts.
- Update the stage ledger with the packet decision.
- Do not write a candidate pack or make paper/live/promotion claims.
