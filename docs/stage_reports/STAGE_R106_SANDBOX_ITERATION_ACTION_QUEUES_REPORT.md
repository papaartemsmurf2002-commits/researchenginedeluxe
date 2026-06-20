# Stage R106 Sandbox Iteration Action Queues Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-266-sandbox-iteration-action-queues.md`
Status: closed

## Summary

WPR106-266 adds deterministic action queues to sandbox iteration index payloads
so agents can immediately find request-bearing, preflight-repair,
missing-brief, and rejection-review iterations.

## Implementation

- Extended `build_sandbox_iteration_index()` with top-level
  `action_queue_version`, `action_queue_limit`, `action_queue_counts`,
  `action_queue_truncated_counts`, and `action_queues` fields.
- Added bounded queue items with sandbox boundary flags, iteration/run identity,
  next action, reason codes, source modes, compact counts, blockers,
  validation-request descriptors, and artifact paths.
- Queue ordering is deterministic and based on request counts, blocker counts,
  rejection counts, and iteration IDs.
- Added focused tests for strict-validation request, preflight-repair, and
  missing-brief queues.

## Boundary

The packet only adds derived action queues to the existing read-only sandbox
iteration index. It does not execute sandbox sweeps, execute strict validation,
write candidate artifacts, change strategy math, change trial IDs, create
paper/live signals, define sizing, place orders, mutate runtime mode, write
live configuration, download provider data, mutate source archive files, or
claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index"
# 2 passed, 93 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 95 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

The action queues are now available in the Python API and guarded CLI payload
because the CLI returns `build_sandbox_iteration_index()` output directly.
Later packets can surface these queues in the operator UI if useful.
