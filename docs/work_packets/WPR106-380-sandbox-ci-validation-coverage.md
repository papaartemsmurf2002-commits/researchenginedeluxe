# WPR106-380 - Sandbox CI Validation Coverage

## Status

closed

## Objective

Close the post-audit H10 CI coverage gap by making the research-validation
workflow run the rapid strategy sandbox test suite and the live CLI boundary
tests that guard sandbox command registration.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-377-sandbox-publication-coherence.md`
- `docs/work_packets/WPR106-378-sandbox-workbook-intake-bounds-and-xls-policy.md`
- `docs/work_packets/WPR106-379-sandbox-source-discovery-bounds.md`

## Allowed paths

- `.github/workflows/research-validation.yml`
- `docs/work_packets/WPR106-380-sandbox-ci-validation-coverage.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_CI_VALIDATION_COVERAGE_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- This packet changes validation coverage only.
- Do not alter sandbox runtime semantics, artifact schemas, strict-validation
  execution, candidate-pack behavior, paper/live behavior, sizing, order
  placement, runtime-mode changes, live config writes, candidate-evidence
  semantics, or promotion state.

## Acceptance criteria

- `.github/workflows/research-validation.yml` runs `tests/research_sandbox`.
- The same workflow runs `tests/live/test_cli_boundary.py` with the existing
  live/artifact boundary tests.
- Local validation proves the added suites pass in the current checkout.
- Diff hygiene passes for the staged packet.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py tests\live\test_cli_boundary.py tests\live\test_reject_research_artifacts.py tests\live\test_shadow_loader.py tests\live\test_promotion_candidate_validator.py -q
python -m compileall -q src\tradingbotsuite
git diff --cached --check
```

Exit evidence:

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `219 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py tests\live\test_cli_boundary.py tests\live\test_reject_research_artifacts.py tests\live\test_shadow_loader.py tests\live\test_promotion_candidate_validator.py -q`
  - `103 passed`
- `python -m compileall -q src\tradingbotsuite`
  - passed

## Stop conditions

- The workflow cannot import the staged sandbox package from a clean checkout.
- Added CI coverage requires provider downloads, generated artifacts, or local
  credentials.
- Any validation change weakens live/research boundary rejection.
