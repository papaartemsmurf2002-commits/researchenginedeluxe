# WPR106-161 Pre-May Component Pocket Control Audit

Status: closed
Date: 2026-06-12
Stage: R106 strategy research

## Objective

Run a May-blind component-level follow-up to WPR106-160. Recent packets found
small May-positive pockets after fixed broad selections, but those observations
must not become May-tuned strategy choices. This packet selects family/component
pockets only from pre-May evidence, then compares their May benchmark behavior
against pre-May-matched controls from the same broad artifact universe.

Optimization and component selection use 2024-01-01 through 2026-04-30 only.
May 2026 is fully excluded from component scoring, row scoring, control
matching, exposure caps, ranking, and selection. May 2026 is used only as a
fixed benchmark after selected components and matched controls are fixed.

## Allowed Paths

- `docs/work_packets/WPR106-161-pre-may-component-pocket-control-audit.md`
- `docs/stage_reports/STAGE_R106_PRE_MAY_COMPONENT_POCKET_CONTROL_AUDIT_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_161_pre_may_component_pocket_control_audit/**`

## Inputs

- Read-only WPR106-157 artifact-universe runner and generated artifacts under
  `data/research/wpr106_157_broad_artifact_component_exposure_selector/**`.
- Read-only local WPR106 selected artifact directories consumed by WPR106-157.

## Method

- Reuse the WPR106-157 artifact-universe builder to normalize local selected
  packet artifacts and recompute common pre-May metrics from trade details.
- Compute row-level pre-May temporal diagnostics without May:
  - 2024-2025 search return and dropout robustness;
  - 2026 Jan-Apr validation return and losing-month count;
  - annual losing-month counts for 2024 and 2025;
  - rolling search-window stability and active trade-rate caps.
- Aggregate rows into component pockets by packet, family, and template.
- Select components only from pre-May evidence, requiring enough rows, high
  validation-positive rate, positive median 2026 Jan-Apr validation return,
  positive median dropout return, and explicit packet/symbol/component caps.
- Select rows inside fixed components using pre-May row scores only.
- Select matched controls from non-selected components using the same pre-May
  row-score distribution, symbols, packets where possible, and trade-count
  bands.
- Replay fixed selected pockets and fixed controls on May 2026 only after all
  pre-May selections are frozen.
- Keep outputs research-only, observe-only, and `promotion_ready: false`.

## Validation

- `python -m compileall -q data/research/wpr106_161_pre_may_component_pocket_control_audit/scripts` -> passed
- `python -m compileall -q src/tradingbotsuite` -> passed
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

## Result

Completed the May-blind pre-May component pocket control audit and wrote the
stage report at
`docs/stage_reports/STAGE_R106_PRE_MAY_COMPONENT_POCKET_CONTROL_AUDIT_REPORT.md`.

The run reused the WPR106-157 artifact universe, included 43 local packet
directories, loaded 2,925 metric rows, 591,571 pre-May trade rows, and 21,216
May benchmark trade rows, and behavior-de-duplicated to 1,915 source rows. It
aggregated 249 component rows, selected 24 components from pre-May evidence,
selected 81 component-pocket rows, and selected 81 matched controls from
non-selected components.

May 2026 benchmarked both fixed groups after pre-May selection. The component
pocket group was less bad than controls, with 19 positive, 60 negative, and 2
flat rows, median -0.015958, and mean -0.015143. The matched-control group had
10 positive, 68 negative, and 3 flat rows, median -0.015520, and mean
-0.020810. The improvement is useful research evidence, but the pocket group
still fails the requested stability profile and is not candidate-ready.

WPR106-146 cross-symbol relative-strength trade-veto rows remained the
strongest research-only pocket with 4/4 May-positive rows, while WPR106-139
calendar/session components and WPR106-137 selected components remained
May-negative. No candidate pack, paper/live artifact, order/sizing/runtime
change, live configuration write, CUDA speedup claim, or promotion claim was
made.

## Exit Criteria

- Write component diagnostics, selected components, selected pocket rows,
  matched control rows, May benchmark metrics for both groups, summary, and
  stage report artifacts.
- Update the stage ledger with the packet decision.
- Do not write a candidate pack or make paper/live/promotion claims.
