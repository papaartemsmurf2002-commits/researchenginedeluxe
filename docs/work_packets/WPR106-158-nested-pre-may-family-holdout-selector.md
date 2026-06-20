# WPR106-158 Nested Pre-May Family Holdout Selector

Status: closed
Date: 2026-06-12
Stage: R106 strategy research

## Objective

Run a May-blind follow-up to WPR106-157 that does not choose rows because of
May 2026 behavior. The packet reuses the broad WPR106 artifact universe but
changes the selector: it ranks rows by nested pre-May family and row stability,
with late pre-May validation, year-balance penalties, rolling holdout evidence,
and exposure caps.

Optimization and selection use 2024-01-01 through 2026-04-30 only. May 2026 is
fully excluded from ranking, family scoring, nested holdout scoring, exposure
caps, and selection. May 2026 is used only as a fixed benchmark holdout after
the selected pre-May rows are fixed.

## Allowed Paths

- `docs/work_packets/WPR106-158-nested-pre-may-family-holdout-selector.md`
- `docs/stage_reports/STAGE_R106_NESTED_PRE_MAY_FAMILY_HOLDOUT_SELECTOR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_158_nested_pre_may_family_holdout_selector/**`

## Inputs

- Read-only WPR106-157 runner and generated artifacts under
  `data/research/wpr106_157_broad_artifact_component_exposure_selector/**`.
- Read-only local WPR106 selected artifact directories consumed by WPR106-157.

## Method

- Reuse the WPR106-157 artifact-universe builder to normalize local selected
  packet artifacts and recompute common pre-May metrics from trade details.
- Compute nested pre-May diagnostics from monthly returns:
  - early pre-May: 2024-01 through 2025-06;
  - late validation: 2025-07 through 2026-04;
  - 2024, 2025, and 2026 Jan-Apr year blocks;
  - six anchored rolling holdouts inherited from WPR106-157.
- Score families/components only from pre-May evidence, rewarding positive
  late validation, low year imbalance, rolling holdout consistency, and active
  but capped trade rates.
- Select rows with strict family/component/packet exposure caps and no May
  feedback.
- Replay the fixed selected set on May 2026 only after pre-May selection.
- Keep outputs research-only, observe-only, and `promotion_ready: false`.

## Validation

- `python -m compileall -q data/research/wpr106_158_nested_pre_may_family_holdout_selector/scripts` -> passed
- `python -m compileall -q src/tradingbotsuite` -> passed
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

## Result

Completed the May-blind nested pre-May selector and wrote the stage report at
`docs/stage_reports/STAGE_R106_NESTED_PRE_MAY_FAMILY_HOLDOUT_SELECTOR_REPORT.md`.

The run reused the WPR106-157 artifact universe, included 43 local packet
directories, loaded 2,925 metric rows, 591,571 pre-May trade rows, and 21,216
May benchmark trade rows, and behavior-de-duplicated to 1,915 source rows. It
found 367 strict nested rows, 588 robust nested rows, and 1,351 late-resilient
rows before selecting a fixed 100-row pre-May set.

The fixed selected set contains 69 `strict_nested`, 30 `robust_nested`, and 1
`late_resilient` rows. Pre-May metrics look strong, with 80 to 1,241 trades,
22 to 28 active months, 1 to 11 losing months, +0.077980 to +2.480657 total
net return, and positive late pre-May returns for every selected row.

May 2026 rejects the fixed set: 23 rows are positive, 75 are negative, and 2
are flat; best May return is +0.067949, worst is -0.133646, median is
-0.017069, and mean is -0.020578. WPR106-146 cross-symbol relative-strength
trade-veto variants remain the clearest research-only May-positive pocket, but
the aggregate selector is not candidate-ready or portfolio-ready.

No candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim was made.

## Exit Criteria

- Write nested source ranking, family/component diagnostics, selected pre-May
  rows/trades, May benchmark, summary, and stage report artifacts.
- Update the stage ledger with the packet decision.
- Do not write a candidate pack or make paper/live/promotion claims.
