# Stage R106 Sandbox Sweep Market Array Cache Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-248-sandbox-sweep-market-array-cache.md`
Status: closed

## Summary

WPR106-248 improves sandbox sweep throughput by preparing market numeric arrays
once per already-filtered 2024+ market frame. Trial execution no longer
reconverts close prices, target/stop high/low prices, or entry-date values for
each venue, filter, exit, and holding-period combination.

## Implementation

- Added a prepared-market array object in
  `src/tradingbotsuite/research_sandbox/fast_backtest.py`.
- The prepared frame now builds close arrays, entry-date arrays, and optional
  high/low arrays once after 2024+ filtering and blueprint signal
  materialization.
- Fixed-hold and target/stop return paths consume the prepared arrays instead
  of converting market columns inside each trial.
- Target/stop exits still require `high` and `low` columns and still return
  explicit blocked rows when those columns are absent.
- Active-day counting now uses the cached entry-date array, preserving the
  existing count while avoiding per-trial timestamp Series extraction.
- The change does not alter deterministic trial IDs, score formulas, ranking,
  blocker reasons, or sandbox boundary payloads.

## Boundary

This packet changes sandbox sweep efficiency only. It does not alter strategy
math, strict validation, candidate-pack gates, live/paper signals, sizing,
order placement, runtime mode, live configuration, provider downloads, or
promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 71 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# final rerun: 461 passed
```

The first full-contract attempt reached 460 passed tests and failed during
pytest-asyncio event-loop socket setup with Windows `WinError 10055`, matching
the already tracked local validation-environment issue. A rerun passed with
461 tests.

## Remaining Work

This cache removes repeated market-array conversion work. Barrier exit path
scans still run per target/stop trial; a later packet can optimize those scans
if profiling shows them to be the next bottleneck.
