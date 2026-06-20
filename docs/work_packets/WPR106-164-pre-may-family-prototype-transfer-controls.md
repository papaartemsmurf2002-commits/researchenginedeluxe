# WPR106-164 Pre-May Family Prototype Transfer Controls

Status: closed
Date: 2026-06-12
Stage: R106 strategy research

## Objective

Run a May-blind broad family/template follow-up after WPR106-163 rejected the
adverse-regime selector but preserved research-only clues in a few pockets.
This packet tests whether any family/template prototypes can be selected from
pre-May group-level stability alone and still transfer to May better than
matched non-selected controls.

The packet must not use May 2026 to pick families, rows, controls, parameters,
or portfolio constructions. May is only a benchmark after all selected
prototypes, rows, controls, and portfolios are frozen.

## Allowed Paths

- `docs/work_packets/WPR106-164-pre-may-family-prototype-transfer-controls.md`
- `docs/stage_reports/STAGE_R106_PRE_MAY_FAMILY_PROTOTYPE_TRANSFER_CONTROLS_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_164_pre_may_family_prototype_transfer_controls/**`

## Inputs

- Read-only WPR106-157 broad artifact normalizer and artifacts under
  `data/research/wpr106_157_broad_artifact_component_exposure_selector/**`.
- Read-only WPR106-163 pre-May adverse-regime selector logic and artifacts may
  be used to reuse pre-May adverse-month/day diagnostics only.

## Method

- Rebuild the broad WPR106 artifact universe from selected trade details.
- Compute pre-May row metrics and adverse-regime diagnostics using only
  2024-01-01 through 2026-04-30.
- Aggregate rows into family/template prototypes by packet, family, template,
  and symbol.
- Score prototypes by group-level pre-May evidence:
  - row count and non-duplicate support;
  - median 2024-2026 Apr return;
  - median 2024-2025 search return;
  - median 2026 Jan-Apr validation return;
  - median adverse-month and adverse-day return;
  - median drop-best-three-month return;
  - annual losing-month profile;
  - active trade rates and cost stress.
- Select prototypes with packet/family/symbol caps using only pre-May evidence.
- Select fixed representative rows from selected prototypes.
- Match non-selected controls by symbol, pre-May score, trade-count scale,
  validation return, and adverse-regime profile.
- Build simple equal-sleeve selected and control portfolios from fixed rows
  using pre-May-only rank/diversity/correlation/overlap diagnostics.
- Benchmark fixed selected rows, matched controls, selected portfolios, and
  control portfolios on May 2026 only after all selections are frozen.
- Keep outputs research-only, observe-only, and `promotion_ready: false`.

## Validation

- `python -m compileall -q data/research/wpr106_164_pre_may_family_prototype_transfer_controls/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

## Exit Criteria

- Write prototype rankings, selected prototype rows, matched controls,
  selected/control portfolio artifacts, May benchmark artifacts, summary, and
  stage report.
- Update the stage ledger with the packet decision.
- Do not write a candidate pack or make paper/live/promotion claims.

## Result

WPR106-164 rebuilt the WPR106-157 broad artifact universe, scored 305
packet/symbol/family/template prototypes from pre-May evidence only, selected
32 fixed prototypes, selected 100 representative rows, matched 100 non-selected
controls, and generated selected/control equal-sleeve portfolios.

May rejected the selected prototype rows and portfolios. Selected prototype
rows had 16 positive, 84 negative, and 0 flat May rows, with best +0.047219,
worst -0.133646, median -0.017170, and mean -0.019284. Matched controls had
16 positive, 79 negative, and 5 flat May rows, with best +0.065272, worst
-0.132690, median -0.015630, and mean -0.015713. Selected prototype
portfolios had 0 positive, 39 negative, and 0 flat May rows, with best
-0.000192, worst -0.047466, median -0.018105, and mean -0.020730.

The run rejects pre-May family/template prototype selection as candidate-ready,
portfolio-ready, or promotion-ready. WPR106-146 relative-strength remains a
narrow research-only pocket; WPR106-128 anchored VWAP remains a research-only
clue that did not pass this stricter pre-May prototype path. The run did not
write a candidate pack, paper/live artifact, live config, order path, sizing
change, CUDA speedup claim, or promotion claim. Focused script compile,
package compile, and contracts passed; contracts reported 460 passed.
