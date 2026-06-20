# WPR106-266 Sandbox Iteration Action Queues

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Make sandbox iteration indexes immediately actionable for agents by adding
deterministic action queues for request-bearing, preflight-repair, missing-brief,
and rejection-review iterations.

## Scope

- Extend `build_sandbox_iteration_index()` payloads with compact action queues
  derived from existing indexed rows.
- Keep queue entries descriptor-only and bounded to existing row metadata:
  iteration IDs, run IDs, next actions, reason codes, counts, top blockers,
  top validation requests, and artifact paths.
- Keep queue ordering deterministic so repeated indexing over unchanged
  manifests produces stable agent worklists.
- Add focused sandbox tests for completed/request-bearing, preflight-blocked,
  and missing-brief queues.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-266-sandbox-iteration-action-queues.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_ACTION_QUEUES_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration_index.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Iteration index JSON payloads include sandbox-boundary-safe action queues and
  queue counts.
- Request-bearing completed iterations appear in the strict-validation request
  queue.
- Preflight-blocked iterations appear in the preflight repair queue.
- Missing brief references/files appear in the missing brief queue.
- Queue entries remain compact and do not execute validation, write candidate
  artifacts, or mutate source artifacts.
- Validation includes focused iteration-index tests, full sandbox tests,
  package compile, import-boundary tests, and the contract baseline when the
  local environment allows it.

## Boundary

This packet only adds derived action queues to the existing read-only sandbox
iteration index. It does not execute sandbox sweeps, execute strict validation,
write candidate artifacts, change strategy math, change trial IDs, create
paper/live signals, define sizing, place orders, mutate runtime mode, write
live configuration, download provider data, mutate source archive files, or
claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. Added deterministic top-level action
queues to `build_sandbox_iteration_index()` payloads:
`strict_validation_request_queue`, `preflight_repair_queue`,
`missing_brief_queue`, and `rejection_review_queue`. Queue items carry sandbox
boundary flags, compact counts, blockers, validation-request descriptors, and
artifact paths derived from existing index rows only.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 2 focused iteration-index tests passed, 95 sandbox tests passed,
package compileall passed, 11 import-boundary tests passed, and 461 contract
tests passed.
