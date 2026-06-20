# Stage R106 Sandbox Iteration Artifact Availability Index Report

Date: 2026-06-19
Work packet: `docs/work_packets/WPR106-278-sandbox-iteration-artifact-availability-index.md`
Status: closed

## Summary

WPR106-278 adds read-only artifact availability diagnostics to sandbox
iteration indexes so agents can find broken iteration references quickly.

## Implementation

- Added artifact availability status, reference count, present count, missing
  count, and missing keys to sandbox iteration index rows.
- Added the same artifact availability context to action queue items and queue
  summaries.
- Added `artifact_repair_queue` for iterations with missing referenced
  artifacts.
- Added top-level index artifact availability status counts and total
  referenced/present/missing artifact counts.
- Bumped the action queue schema version to 5.

## Boundary

This packet only adds read-only path-existence diagnostics to sandbox iteration
indexes and queues. It does not download provider data, execute sandbox sweeps
beyond tests, execute strict validation, write candidate artifacts, create
paper/live signals, define sizing, place orders, mutate runtime mode, write
live configuration, mutate source archive files, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index or action_queue_rollups"
# 5 passed, 110 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 115 passed

$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```
