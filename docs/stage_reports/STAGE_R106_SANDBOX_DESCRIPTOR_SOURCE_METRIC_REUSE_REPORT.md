# Stage R106 Sandbox Descriptor Source Metric Reuse Report

Date: 2026-06-19
Work packet: `docs/work_packets/WPR106-282-sandbox-descriptor-source-metric-reuse.md`
Status: closed

## Summary

WPR106-282 speeds up archive-backed sandbox sweeps by reusing trial metric work
across venue descriptors that share the same explicit market source.

## Implementation

- Grouped descriptor-routed sweeps by shared market-data path, identical
  descriptor `data_path`, or the same in-memory market frame object.
- Reused the existing per-market trial metric cache across venues in the same
  source group.
- Preserved venue-specific trial IDs, venue fields, source metadata, and global
  ranking.
- Preserved separate metric computation for descriptors with distinct market
  sources.

## Boundary

This packet only changes research-sandbox metric reuse inside existing
archive-backed sweeps. It does not change backtest assumptions, execute strict
validation, write candidate artifacts, create paper/live signals, define
sizing, place orders, mutate runtime mode, write live configuration, mutate
source archive files, download provider data, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "shared_market_sweep_reuses_trial_metrics or descriptor_routed_sweep"
# 3 passed, 113 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 116 passed

$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```
