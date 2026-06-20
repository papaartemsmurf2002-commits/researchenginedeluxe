# Stage R106 Sandbox Archive Coverage Requested Window Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-272-sandbox-archive-coverage-requested-window.md`
Status: closed

## Summary

WPR106-272 makes archive audit and coverage diagnostics aware of the active
sandbox requested data window so existing venue archive manifests can be
triaged before preflight and sweep execution.

## Implementation

- Added optional requested-window metadata to sandbox archive descriptor audits.
- Audit rows now report requested-window row counts and observed bounds
  separately from descriptor-window counts.
- Loadable descriptors with no rows in the requested window are blocked with
  `no_rows_in_requested_window`.
- Archive coverage rows aggregate requested-window counts, observed bounds, and
  blocker reasons by venue/symbol/data-family/interval bucket.
- One-command sandbox iterations pass their resolved spec data window into
  archive coverage for existing venue archive manifests and built archive-root
  manifests.
- Archive audit and coverage CLI handlers accept optional requested-window
  bounds for direct agent diagnostics.

## Boundary

This packet only adds requested-window diagnostics to sandbox archive audit and
coverage artifacts. It does not download provider data, execute strict
validation, write candidate artifacts, create paper/live signals, define
sizing, place orders, mutate runtime mode, write live configuration, mutate
source archive files, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "requested_window or existing_archive_coverage or audits_archive_descriptors_under_research_root or summarizes_archive_coverage_under_research_root"
# 6 passed, 106 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 112 passed

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
# 22 passed

$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```
