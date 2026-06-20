# Stage R106 Sandbox Full Archive Blocker Counts Report

Date: 2026-06-19
Work packet: `docs/work_packets/WPR106-274-sandbox-full-archive-blocker-counts.md`
Status: closed

## Summary

WPR106-274 makes sandbox archive-window repair queues robust by writing full
archive coverage blocker counts to iteration manifests, agent briefs, and
iteration indexes.

## Implementation

- Added full `archive_coverage_blocker_reason_counts` to one-command sandbox
  iteration manifests.
- Added full `archive_blocker_reason_counts` to agent briefs while preserving
  the compact `top_archive_blockers` display list.
- Iteration index rows and action queue items now preserve full archive
  blocker counts.
- `archive_window_repair_queue` now prefers full blocker counts when checking
  for `no_rows_in_requested_window` and falls back to top blockers only for
  older artifacts.

## Boundary

This packet only adds read-only blocker-count metadata to sandbox iteration
manifests, briefs, and indexes. It does not download provider data, execute
sandbox sweeps beyond tests, execute strict validation, write candidate
artifacts, create paper/live signals, define sizing, place orders, mutate
runtime mode, write live configuration, mutate source archive files, or claim
promotion readiness.

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
