# WPR106-264 Sandbox Iteration Index

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Add a compact research-only iteration index that scans sandbox agent iteration
manifests and briefs across an output root, so agents can find completed,
preflight-blocked, request-bearing, and repair-needed iterations without
opening every iteration directory.

## Scope

- Add a sandbox iteration index API that writes
  `sandbox_iteration_index.json` and `sandbox_iteration_index.parquet`.
- Index iteration status, next action, reason codes, coverage/preflight/result
  counts, request counts, artifact paths, and brief availability.
- Validate sandbox boundary flags on source iteration manifests and loaded
  briefs.
- Make the index discoverable by the sandbox artifact catalog.
- Export the API from `tradingbotsuite.research_sandbox`.
- Add focused sandbox tests covering multiple iterations, old/missing brief
  references, and catalog discovery.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-264-sandbox-iteration-index.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_INDEX_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration_index.py`
- `src/tradingbotsuite/research_sandbox/__init__.py`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- The index writes JSON/Parquet artifacts with sandbox boundary flags and row
  summaries for multiple iteration manifests.
- Rows surface next-action, reason-code, coverage, preflight, result, and
  descriptor-only validation request counts.
- Rows distinguish present briefs from missing brief references without
  treating old/incomplete iterations as candidate evidence.
- Existing brief files must retain sandbox boundary flags when indexed.
- Sandbox artifact catalog discovery includes `iteration_index`.
- Validation includes focused sandbox tests, full sandbox tests, package
  compile, import-boundary tests, and the contract baseline when the local
  environment allows it.

## Boundary

This packet only adds a read-only research index over existing sandbox
iteration artifacts. It does not execute sandbox sweeps, execute strict
validation, write candidate artifacts, change strategy math, change trial IDs,
create paper/live signals, define sizing, place orders, mutate runtime mode,
write live configuration, download provider data, mutate source archive files,
or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. Added
`build_sandbox_iteration_index()` and the `sandbox_iteration_index.json` /
`sandbox_iteration_index.parquet` artifact pair. The index scans existing
iteration manifests and agent briefs, validates sandbox boundary flags,
summarizes statuses, next actions, reason codes, coverage/preflight/result
counts, descriptor-only request counts, blocker summaries, validation-request
descriptors, brief availability, and artifact paths. The sandbox artifact
catalog now discovers `iteration_index`.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 2 focused iteration-index tests passed, 94 sandbox tests passed,
package compileall passed, 11 import-boundary tests passed, and 461 contract
tests passed.
