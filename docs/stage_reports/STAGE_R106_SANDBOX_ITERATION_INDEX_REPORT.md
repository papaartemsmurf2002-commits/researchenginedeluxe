# Stage R106 Sandbox Iteration Index Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-264-sandbox-iteration-index.md`
Status: closed

## Summary

WPR106-264 adds a compact research-only iteration index for agent navigation
across one-command sandbox iterations.

## Implementation

- Added `tradingbotsuite.research_sandbox.iteration_index`.
- Added `build_sandbox_iteration_index(root_dir, output_dir=..., max_files=...)`
  to scan `sandbox_iteration_manifest.json` files and load available
  `sandbox_iteration_agent_brief.json` files.
- The index writes `sandbox_iteration_index.json` and
  `sandbox_iteration_index.parquet` with iteration status, next action, reason
  codes, brief status, coverage counts, preflight counts, result counts,
  request counts, top blockers, top validation-request descriptors, and
  artifact paths.
- Source iteration manifests and loaded briefs must retain sandbox boundary
  flags. Missing brief references or missing brief files are surfaced as row
  `brief_status` values instead of being treated as candidate evidence.
- Exported the API from `tradingbotsuite.research_sandbox`.
- Added `sandbox_iteration_index.json` to sandbox artifact catalog discovery as
  `iteration_index`.
- Updated the sandbox research contract and active index.

## Boundary

The packet only adds a read-only research index over existing sandbox iteration
artifacts. It does not execute sandbox sweeps, execute strict validation, write
candidate artifacts, change strategy math, change trial IDs, create paper/live
signals, define sizing, place orders, mutate runtime mode, write live
configuration, download provider data, mutate source archive files, or claim
promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index"
# 2 passed, 92 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 94 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

The Python API and artifact catalog path are in place. A later packet can add a
guarded CLI command for generating iteration indexes under the configured
research output root.
