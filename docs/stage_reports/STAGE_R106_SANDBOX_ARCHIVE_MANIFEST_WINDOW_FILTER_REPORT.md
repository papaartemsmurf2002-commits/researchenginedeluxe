# Stage R106 Sandbox Archive Manifest Window Filter Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-271-sandbox-archive-manifest-window-filter.md`
Status: closed

## Summary

WPR106-271 makes archive-root based sandbox iterations cheaper by filtering
archive manifest materialization to the already resolved sandbox data window.

## Implementation

- Added optional `requested_window` filtering to
  `build_sandbox_archive_manifest`.
- The builder now includes only local files whose normalized 2024+ timestamp
  bounds overlap the requested window.
- Out-of-window files are retained in the build report as skipped rows with
  `outside_requested_window`.
- Build reports and generated manifests record requested-window metadata.
- One-command sandbox iterations now resolve the spec/window before archive
  root materialization and pass that window into the archive manifest builder.
- Existing venue archive manifest inputs keep their current behavior.

## Boundary

This packet only filters local sandbox archive manifest construction before
preflight. It does not download provider data, execute strict validation, write
candidate artifacts, create paper/live signals, define sizing, place orders,
mutate runtime mode, write live configuration, mutate source archive files, or
claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "requested_window or filters_archive_roots"
# 2 passed, 107 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 109 passed

$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

Future packets may add filename-level prefilters for known venue archive naming
schemes if large local drops still spend too much time loading out-of-window
files.
