# WPR106-278 Sandbox Iteration Artifact Availability Index

Status: closed
Owner: Codex Research Agent
Created: 2026-06-19

## Objective

Make sandbox iteration indexes report whether referenced iteration artifacts
still exist so agents can repair or rerun broken archive-backed iterations from
the index manifest before opening nested JSON/Parquet outputs.

## Scope

- Add read-only artifact availability counts to iteration index rows.
- Check only already-referenced artifact paths from iteration manifests, agent
  briefs, and source-context path fields.
- Report missing artifact keys without opening or mutating the referenced
  artifacts.
- Include artifact availability fields in action queue items and queue
  summaries.
- Add an `artifact_repair_queue` for iterations with missing referenced
  artifacts.
- Preserve existing missing-brief behavior and all existing queue semantics.
- Bump the action queue schema version.
- Add focused sandbox tests proving missing non-brief artifacts appear in rows,
  queue items, queue summaries, and the new repair queue.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-278-sandbox-iteration-artifact-availability-index.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_ARTIFACT_AVAILABILITY_INDEX_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration_index.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Iteration index rows include `artifact_availability_status`, referenced,
  present, and missing artifact counts, plus missing artifact keys.
- Action queue items carry the same artifact availability context.
- Index payloads include artifact availability status totals and an
  `artifact_repair_queue`.
- Existing preflight, archive-window, missing-brief, request, and rejection
  queues remain stable.
- The index remains read-only: it must not open child artifacts for validation,
  mutate artifacts, execute sandbox sweeps, execute strict validation, or write
  candidate artifacts.
- Validation includes focused sandbox tests, full sandbox tests, package
  compile, import-boundary tests, and the contract baseline when the local
  environment allows it.

## Boundary

This packet only adds read-only path-existence diagnostics to sandbox iteration
indexes and queues. It does not download provider data, execute sandbox sweeps
beyond tests, execute strict validation, write candidate artifacts, create
paper/live signals, define sizing, place orders, mutate runtime mode, write
live configuration, mutate source archive files, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-19. Sandbox iteration index rows now include
`artifact_availability_status`, artifact reference/present/missing counts, and
missing artifact keys. Queue items and queue summaries carry the same
availability context, and indexes include an `artifact_repair_queue` for
iterations with missing referenced artifacts.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index or action_queue_rollups"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 5 focused iteration-index/action-queue tests passed, 115
sandbox tests passed, package compileall passed, 11 import-boundary tests
passed, and 461 contract tests passed.
