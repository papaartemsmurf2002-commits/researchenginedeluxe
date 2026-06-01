# Stage R106 Mode-Aware Artifact Runtime Validation Report

Date: 2026-05-31

Work packet:
`docs/work_packets/WPR106-38-mode-aware-artifact-runtime-validation.md`

## Scope

Closed `ISSUE-R106-014` by making artifact runtime loading fail closed by
runtime mode before any scorer or shadow-loader construction.

This packet did not add live, paper, order-placement, promotion, sizing,
strategy, model, filter, candidate-pack writing, or generated research behavior.

## Changes

- Added `validate_artifact_for_runtime_mode()` in
  `src/tradingbotsuite/promotion/artifact_validator.py`.
- Tightened `validate_artifact_for_live_input()` so minimal promoted manifests
  missing explicit live-boundary fields and runtime-mode declarations fail
  closed.
- Exported the new validator from `tradingbotsuite.promotion`.
- Updated live preflight to validate configured artifacts through the
  mode-aware contract. Artifact checks now activate for non-live modes whenever
  an artifact path is configured.
- Updated `runtime.build_engine()` to validate artifact manifests before
  dispatching to the shadow loader or `AcceptanceScorer`.
- Tightened shadow loader runtime declarations so shadow candidates must
  explicitly permit shadow runtime.

## Runtime Contract

- `live`: rejects research-only, observe-only, shadow-only, promotion-candidate,
  unknown, mode-ambiguous, and missing-boundary manifests.
- `paper`: rejects runtime artifact loading until a later explicit
  paper-runtime artifact contract exists.
- `shadow`: allows only explicit shadow promotion candidates that pass the
  existing shadow validator and declare shadow runtime allowance.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\live\test_reject_research_artifacts.py tests\live\test_promotion_candidate_validator.py tests\live\test_shadow_loader.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts\test_candidate_pack.py -q
$env:PYTHONPATH='src'; python -m pytest tests\live -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Results:

- compile passed
- focused live artifact/promotion/shadow tests: 17 passed
- candidate-pack artifact tests: 37 passed
- full live slice: 63 passed
- contracts: 430 passed
- diff check passed with line-ending warnings only

## Boundary Statement

Runtime artifact loading is now fail-closed by mode. Research artifacts remain
non-live and non-promotable. Candidate gates were not weakened, and zero
eligible candidates remains valid evidence.

## Remaining Blockers

- Active P0 count: 0.
- `ISSUE-R104-001` remains open as a P1: candidate-ready empirical evidence
  still requires durable candidate-depth data and downstream validation.
