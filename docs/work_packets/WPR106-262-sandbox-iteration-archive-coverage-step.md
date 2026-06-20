# WPR106-262 Sandbox Iteration Archive Coverage Step

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Make the one-command sandbox agent iteration produce the archive coverage
matrix as a first-class iteration step before compatibility preflight, so every
agent run records venue/symbol/data-family/interval readiness and cached
iteration reuse depends on that coverage evidence.

## Scope

- Call the sandbox archive coverage summarizer from
  `run_sandbox_agent_iteration` after archive manifest intake/materialization
  and before compatibility preflight.
- Add archive coverage JSON/Parquet paths and counts to the iteration manifest.
- Add an `archive_coverage_matrix` row to iteration steps for completed and
  preflight-blocked runs.
- Require cached iteration reuse to validate the coverage JSON boundary flags
  and coverage Parquet file existence.
- Add focused sandbox tests for completed iterations, blocked iterations, and
  missing cached coverage artifacts.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-262-sandbox-iteration-archive-coverage-step.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_ARCHIVE_COVERAGE_STEP_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Completed sandbox agent iterations include `archive_coverage_json_path`,
  `archive_coverage_parquet_path`, coverage counts, and an
  `archive_coverage_matrix` step.
- Preflight-blocked sandbox agent iterations still include the archive coverage
  matrix before downstream sweep/analysis steps are skipped.
- Cached iteration reuse fails closed when archive coverage JSON or Parquet
  artifacts are missing or lose sandbox boundary metadata.
- Validation includes focused sandbox tests, full sandbox tests, package
  compile, import-boundary tests, and the contract baseline when the local
  environment allows it.

## Boundary

This packet only adds archive-readiness evidence to research-only sandbox
iteration manifests. It does not change strategy math, trial identities, sweep
execution semantics, strict validation execution, candidate-pack generation,
paper/live signals, sizing, order placement, runtime mode, live configuration,
provider downloads, source archive mutation, or promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. The sandbox agent iteration now writes an
archive coverage matrix immediately after archive manifest intake and before
compatibility preflight. Completed and preflight-blocked iteration manifests
record coverage JSON/Parquet paths, source-audit JSON/Parquet paths,
descriptor counts, bucket counts, status counts, and venue counts. Cached
iteration reuse now validates coverage/source-audit JSON boundary flags and
coverage/source-audit Parquet existence before returning `reused_existing:
true`.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "agent_iteration and (coverage or materializes or skips_downstream or runs_sandbox_agent_iteration_under_research_root)"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 5 focused iteration tests passed, 90 sandbox tests passed,
package compileall passed, 11 import-boundary tests passed, and 461 contract
tests passed. `git diff --check` reported only existing LF-to-CRLF
working-copy warnings and no whitespace errors.
