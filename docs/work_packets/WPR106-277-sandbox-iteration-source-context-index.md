# WPR106-277 Sandbox Iteration Source Context Index

Status: closed
Owner: Codex Research Agent
Created: 2026-06-19

## Objective

Make sandbox iteration indexes expose strategy-catalog and venue-archive source
context directly in rows and action queue items so agents can repair archive
roots, skipped source files, and materialized inputs without reopening every
iteration manifest or step parquet.

## Scope

- Add source-context fields from one-command iteration `strategy_source` and
  `archive_source` objects to iteration index rows.
- Include strategy catalog/build-report paths and included/skipped source
  counts when present.
- Include venue archive manifest/build-report paths plus archive file and
  skipped-file counts when present.
- Include those source-context fields in action queue items and queue summary
  numeric rollups.
- Preserve existing action queues, source manifests, artifact paths, and
  sandbox boundary flags.
- Bump the action queue schema version.
- Add focused sandbox tests proving indexed rows and queues expose materialized
  source context, including archive files skipped by requested-window filtering.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-277-sandbox-iteration-source-context-index.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_SOURCE_CONTEXT_INDEX_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration_index.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Iteration index rows include source catalog/archive paths and source-count
  metadata when the iteration manifest contains it.
- Action queue items include the same source-context fields for direct agent
  triage.
- Queue summaries aggregate source skipped-count and file/source-count metadata
  across matched rows.
- Requested-window archive materialization skips are visible from an iteration
  index without reopening the archive build report.
- Existing older artifacts missing these fields remain indexable with empty or
  zero defaults.
- Validation includes focused sandbox tests, full sandbox tests, package
  compile, import-boundary tests, and the contract baseline when the local
  environment allows it.

## Boundary

This packet only adds read-only source-context metadata to sandbox iteration
indexes and queues. It does not download provider data, execute sandbox sweeps
beyond tests, execute strict validation, write candidate artifacts, create
paper/live signals, define sizing, place orders, mutate runtime mode, write
live configuration, mutate source archive files, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-19. Sandbox iteration index rows and action
queue items now expose strategy-catalog and venue-archive source context,
including catalog/archive manifest paths, build-report paths, included/skipped
strategy source counts, archive file counts, and archive skipped-file counts.
Action queue summaries aggregate those source counts across all matched rows.

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
