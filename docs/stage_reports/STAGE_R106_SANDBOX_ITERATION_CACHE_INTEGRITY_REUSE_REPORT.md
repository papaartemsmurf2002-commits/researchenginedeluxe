# Stage R106 Sandbox Iteration Cache Integrity Reuse Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-256-sandbox-iteration-cache-integrity-reuse.md`
Status: closed

## Summary

WPR106-256 makes cached one-command sandbox iteration reuse fail closed when
referenced artifacts are missing, no longer carry sandbox boundary flags, or
when a completed iteration's referenced run child artifacts no longer match
manifest-recorded integrity metadata.

## Implementation

- Added cached artifact reference validation to
  `src/tradingbotsuite/research_sandbox/iteration.py`.
- Cached JSON artifacts are loaded and checked for sandbox boundary flags
  before reuse.
- Cached Parquet artifacts are checked for existence before reuse.
- Completed cached iterations verify the referenced run manifest's child
  artifact SHA-256 and byte-size metadata before returning
  `reused_existing: true`.
- Untampered cached iterations still reuse the existing manifest for fast agent
  iteration.

## Boundary

The packet changes cached iteration reuse validation only. It does not execute
new sweeps on the reuse path, execute strict validation, change strategy math,
change trial IDs, write candidate packs, create paper/live signals, define
sizing, place orders, change runtime mode, write live configuration, download
provider data, mutate source artifacts, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "agent_iteration"
# 7 passed, 77 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 84 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

The cached iteration path now refuses missing or stale references. Later
packets can add integrity metadata to iteration-level derived reports
themselves if agents need hash checks beyond existence plus boundary validation
for non-run artifacts.
