# WPR106-276 Sandbox Action Queue Rollups

Status: closed
Owner: Codex Research Agent
Created: 2026-06-19

## Objective

Make sandbox iteration indexes expose queue-level status and reason rollups so
agents can triage large iteration backlogs from the index manifest without
reopening every iteration row, agent brief, coverage report, or preflight
artifact.

## Scope

- Add action-queue summaries to sandbox iteration indexes.
- Summaries should cover every matched queue row, not only the bounded visible
  queue items.
- Preserve existing bounded action queue items and stable queue ordering.
- Include compact queue-level iteration status, next-action, coverage status,
  archive blocker, preflight status, preflight blocker, and key numeric count
  rollups.
- Include coverage and preflight status counts in queue items for fast per-item
  repair triage.
- Bump the action queue schema version.
- Add focused sandbox tests proving queue summaries aggregate full matched
  queues while queue items remain bounded and non-promotable.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-276-sandbox-action-queue-rollups.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ACTION_QUEUE_ROLLUPS_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration_index.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Iteration index payloads include deterministic `action_queue_summaries`.
- Queue summaries aggregate all matched rows for each queue even when the
  visible queue item list is capped.
- Queue items include coverage and preflight status counts.
- Existing action queues remain bounded, ordered, descriptor-only, and
  sandbox-boundary compliant.
- Validation includes focused sandbox tests, full sandbox tests, package
  compile, import-boundary tests, and the contract baseline when the local
  environment allows it.

## Boundary

This packet only adds read-only iteration-index summary metadata. It does not
download provider data, execute sandbox sweeps beyond tests, execute strict
validation, write candidate artifacts, create paper/live signals, define
sizing, place orders, mutate runtime mode, write live configuration, mutate
source archive files, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-19. Sandbox iteration indexes now write
`action_queue_summaries` for every action queue. Summaries aggregate all
matched rows, including rows hidden by the visible queue limit, and queue items
now include coverage and preflight status counts for direct triage.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index or action_queue_rollups"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 4 focused iteration-index/action-queue tests passed, 114
sandbox tests passed, package compileall passed, 11 import-boundary tests
passed, and 461 contract tests passed.
