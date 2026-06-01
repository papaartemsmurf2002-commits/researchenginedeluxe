# WPR106-38 Mode-Aware Artifact Runtime Validation

## Goal

Close `ISSUE-R106-014` by adding a mode-aware
`validate_artifact_for_runtime_mode()` contract and using it before runtime,
paper, shadow, or live artifact loading. Unknown or mode-ambiguous manifests
must fail closed.

This packet must not add new promotion logic, strategy logic, live/paper
execution behavior, order placement, sizing, or research candidate generation.

## Current Repo Facts

- `validate_artifact_for_live_input()` rejects explicit research, observe-only,
  and non-promotion-ready fields, but a minimal unknown manifest with
  `promotion_ready: true` can be accepted.
- `live.preflight._check_research_artifact()` calls the live-input validator
  only when live preflight is active.
- `runtime.build_engine()` calls live preflight first, then loads any existing
  configured artifact path. Promotion-candidate manifests go through the shadow
  loader; non-candidate manifests go directly into `AcceptanceScorer`.
- `RuntimeMode` currently has `shadow`, `paper`, and `live`.
- Shadow promotion-candidate loading already has a strict shadow validator, but
  there is no central runtime-mode validation before runtime artifact dispatch.

## Conflicts And Stale Docs Found

- `docs/KNOWN_ISSUES.md` correctly says generic live-input validation can allow
  unknown minimal manifests and lacks `validate_artifact_for_runtime_mode()`.
- Existing runtime behavior predates the active P0 rule and can load artifacts
  in non-live modes without an explicit mode-aware boundary.

## Allowed Edit Paths

- `docs/work_packets/WPR106-38-mode-aware-artifact-runtime-validation.md`
- `docs/work_packets/WPR106-38-progress.jsonl`
- `src/tradingbotsuite/promotion/artifact_validator.py`
- `src/tradingbotsuite/promotion/__init__.py`
- `src/tradingbotsuite/live/preflight.py`
- `src/tradingbotsuite/runtime.py`
- `tests/live/test_reject_research_artifacts.py`
- `tests/live/test_promotion_candidate_validator.py`
- `tests/live/test_shadow_loader.py`
- focused tests under `tests/live/**` and `tests/research_artifacts/**` if
  needed for the validator contract
- `docs/ACTIVE_INDEX.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_MODE_AWARE_ARTIFACT_RUNTIME_VALIDATION_REPORT.md`

## Forbidden Edit Paths

- execution adapters and order-placement behavior
- research strategies, filters, models, candidate gates, generated data, and
  candidate-pack writing
- live runtime mode switching behavior beyond adding fail-closed artifact
  validation
- fixture data and generated research artifacts
- `.pytest_cache/**`

## Subagents Used

- Artifact Gatekeeper: inspect current artifact validator/runtime fail-open
  paths and propose the smallest fail-closed mode-aware contract.

## Tests To Run

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\live\test_reject_research_artifacts.py tests\live\test_promotion_candidate_validator.py tests\live\test_shadow_loader.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts\test_candidate_pack.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Artifacts Expected

- New mode-aware validator contract.
- Runtime and live-preflight use of that contract.
- Tests proving unknown manifests and research/observe-only manifests fail
  closed in runtime modes.
- Tests proving valid shadow-only promotion candidates remain shadow-only and
  are rejected for paper/live runtime artifact loading.
- Updated issue registry and stage report.

No live order, paper order, runtime mutation, candidate pack, generated
research data artifact, or promotion-ready claim is expected.

## Definition Of Done

- Unknown or minimal mode-ambiguous manifests fail closed for live, paper, and
  shadow runtime loading.
- Live mode rejects research-only, observe-only, shadow-only, unknown, and
  missing-boundary manifests through the mode-aware validator.
- Paper mode rejects research, shadow-only, promotion candidates, and unknown
  artifacts instead of loading scorer artifacts.
- Shadow mode only allows promotion-candidate manifests that pass the existing
  shadow validator; unknown and research-only artifacts fail closed.
- Runtime dispatch calls the mode-aware validator before scorer or shadow-loader
  construction.
- `ISSUE-R106-014` is resolved only after focused and contract validation
  passes.

## Rollback Plan

Revert only files in the allowed edit paths. Do not touch execution adapters,
order placement, research candidates, generated artifacts, local credentials,
or unrelated cache state.
