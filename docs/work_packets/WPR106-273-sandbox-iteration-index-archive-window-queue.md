# WPR106-273 Sandbox Iteration Index Archive Window Queue

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Expose requested-window archive coverage blockers in sandbox iteration indexes
so agents can repair existing multi-venue archive manifests without reopening
each iteration's coverage JSON.

## Scope

- Add requested-window archive coverage counts to sandbox iteration index rows.
- Include requested-window archive coverage counts in action queue items.
- Add a bounded `archive_window_repair_queue` for iterations whose archive
  blockers include `no_rows_in_requested_window`.
- Bump the iteration action queue schema version.
- Keep the existing strict-validation request, preflight-repair,
  missing-brief, and rejection-review queues stable.
- Add focused sandbox tests for the new queue and update existing exact queue
  expectations.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-273-sandbox-iteration-index-archive-window-queue.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_INDEX_ARCHIVE_WINDOW_QUEUE_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration_index.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Iteration index rows expose `archive_coverage_requested_window_row_count`.
- Queue items expose the same requested-window archive coverage count.
- `archive_window_repair_queue` contains iterations with
  `no_rows_in_requested_window` archive blockers.
- Existing queue behavior for strict-validation requests, preflight repairs,
  missing briefs, and rejection review remains intact.
- Queue payloads and rows keep required sandbox boundary flags and do not
  execute sandbox sweeps or strict validation.
- Validation includes focused sandbox tests, full sandbox tests, package
  compile, import-boundary tests, and the contract baseline when the local
  environment allows it.

## Boundary

This packet only changes read-only sandbox iteration indexes over existing
iteration manifests and briefs. It does not download provider data, execute
sandbox sweeps, execute strict validation, write candidate artifacts, create
paper/live signals, define sizing, place orders, mutate runtime mode, write
live configuration, mutate source archive files, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. Sandbox iteration index rows now expose
`archive_coverage_requested_window_row_count`, queue item counts include the
same value, and action queue schema version 2 adds a bounded
`archive_window_repair_queue` for rows whose archive blockers include
`no_rows_in_requested_window`. Existing strict-validation request,
preflight-repair, missing-brief, and rejection-review queues remain present.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 3 focused iteration-index tests passed, 113 sandbox tests
passed, package compileall passed, 11 import-boundary tests passed, and 461
contract tests passed.
