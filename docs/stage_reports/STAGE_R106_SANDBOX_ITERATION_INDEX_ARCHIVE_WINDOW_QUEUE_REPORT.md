# Stage R106 Sandbox Iteration Index Archive Window Queue Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-273-sandbox-iteration-index-archive-window-queue.md`
Status: closed

## Summary

WPR106-273 surfaces requested-window archive coverage blockers in sandbox
iteration indexes so agents can find archive-window repair work directly from
the index artifact.

## Implementation

- Added `archive_coverage_requested_window_row_count` to iteration index rows.
- Added the same requested-window count to action queue item counts.
- Added bounded `archive_window_repair_queue` entries for iterations whose top
  archive blockers include `no_rows_in_requested_window`.
- Bumped the iteration action queue schema version to 2.
- Preserved the existing strict-validation request, preflight-repair,
  missing-brief, and rejection-review queues.

## Boundary

This packet only changes read-only sandbox iteration indexes over existing
iteration manifests and briefs. It does not download provider data, execute
sandbox sweeps, execute strict validation, write candidate artifacts, create
paper/live signals, define sizing, place orders, mutate runtime mode, write
live configuration, mutate source archive files, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index"
# 3 passed, 110 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 113 passed

$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```
