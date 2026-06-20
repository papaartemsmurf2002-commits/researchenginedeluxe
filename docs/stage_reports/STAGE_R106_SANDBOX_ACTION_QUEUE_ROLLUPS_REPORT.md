# Stage R106 Sandbox Action Queue Rollups Report

Date: 2026-06-19
Work packet: `docs/work_packets/WPR106-276-sandbox-action-queue-rollups.md`
Status: closed

## Summary

WPR106-276 adds queue-level rollups to sandbox iteration indexes so agents can
triage large action queues from one manifest.

## Implementation

- Added `action_queue_summaries` to sandbox iteration index payloads.
- Queue summaries aggregate all matched rows for each queue, including rows
  hidden by the visible action-queue limit.
- Queue summaries expose iteration-status, next-action, coverage-status,
  archive-blocker, preflight-status, preflight-blocker, and numeric count
  rollups.
- Queue items now carry coverage and preflight status counts.
- Bumped the action queue schema version to 3.

## Boundary

This packet only adds read-only iteration-index summary metadata. It does not
download provider data, execute sandbox sweeps beyond tests, execute strict
validation, write candidate artifacts, create paper/live signals, define
sizing, place orders, mutate runtime mode, write live configuration, mutate
source archive files, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index or action_queue_rollups"
# 4 passed, 110 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 114 passed

$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```
