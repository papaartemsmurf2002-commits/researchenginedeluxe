# Stage R106 Sandbox Suite Preflight Gate Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-246-sandbox-suite-preflight-gate.md`
Status: closed

## Summary

WPR106-246 makes compatibility preflight part of sandbox suite execution.
Suite batches now expose case-level runnable/blocked trial estimates and avoid
spending sweep time on cases that have no runnable strategy/archive trials.

## Implementation

- Added per-case `preflight_sandbox_compatibility()` execution inside
  `run_sandbox_suite()`.
- Wrote preflight artifacts under each suite directory at
  `preflights/<case_id>/<preflight_id>/`.
- Added preflight paths, row counts, status counts, runnable/blocked trial
  estimates, and blocker reason counts to suite case-index rows.
- Added suite-level aggregate preflight counts, completed case counts, and
  skipped case counts to `suite_manifest.json`.
- Preserved existing runnable case behavior: archive sweep, run analysis, and
  suite evidence-request aggregation still run when preflight finds runnable
  trials.
- Added a zero-runnable case path: suite indexes record
  `case_status: blocked_by_preflight`, no run artifact paths, zero result
  counts, and zero evidence-request counts.
- Hardened suite hypothesis summarization to skip intentional
  `blocked_by_preflight` rows while still rejecting malformed non-blocked
  rows missing `run_dir`.
- Added suite CLI payload counts for completed/skipped cases and preflight
  trial estimates.

## Boundary

This packet changes suite orchestration only. It does not alter sandbox scoring
math, execute strict validation, write candidate packs, create paper/live
signals, define sizing, place orders, mutate runtime mode, write live
configuration, download provider data, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 69 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

This packet does not change strategy generation or scoring. It makes suite
batch execution cheaper and more diagnosable when cases are blocked by missing
archive columns, missing signals, or empty 2024+ windows.
