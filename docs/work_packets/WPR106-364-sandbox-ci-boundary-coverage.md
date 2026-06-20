# WPR106-364 - Sandbox CI Boundary Coverage

## Status

closed

## Objective

Add the Rapid Strategy Iteration Sandbox suite and live CLI boundary tests to
the checked-in research validation workflow so sandbox regressions and command
boundary regressions are not invisible to CI.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-362-post-audit-sandbox-safety-coherence.md`
- `docs/work_packets/WPR106-363-red-test-repair-strategy-discovery-resume.md`

## Allowed paths

- `.github/workflows/research-validation.yml`
- `docs/work_packets/WPR106-364-sandbox-ci-boundary-coverage.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_CI_BOUNDARY_COVERAGE_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- Workflow-only validation coverage change.
- No code, config semantics, generated artifact, archive manifest/source
  mutation, provider download, replay execution, strict-validation execution,
  candidate pack, paper/live artifact, sizing, order behavior, runtime-mode
  change, live configuration write, or promotion state change.

## Acceptance criteria

- CI runs `tests/research_sandbox` and `tests/live/test_cli_boundary.py`.
- Existing contract and live/artifact boundary checks remain in the workflow.
- Local focused validation for the newly added test targets passes.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
git diff --check
```
