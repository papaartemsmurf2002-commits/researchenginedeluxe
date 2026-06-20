# Stage R106 Sandbox Iteration Recommended Actions Report

Date: 2026-06-19
Work packet: `docs/work_packets/WPR106-279-sandbox-iteration-recommended-actions.md`
Status: closed

## Summary

WPR106-279 adds deterministic recommended action hints to sandbox iteration
indexes so agents can move from queue triage to the next repair or review step
without reopening every nested artifact.

## Implementation

- Added `recommended_actions` and primary `recommended_action` fields to
  sandbox iteration index rows.
- Added the same recommended action context to action queue items.
- Added recommended-action rollups to queue summaries and top-level index
  payloads.
- Mapped common blocker contexts to deterministic repair/review hints for
  missing briefs, missing referenced artifacts, archive-window blockers,
  preflight blockers, strict-validation request descriptors, and rejection
  review cases.
- Bumped the action queue schema version to 6.

## Boundary

This packet only adds deterministic navigation hints to sandbox iteration
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
