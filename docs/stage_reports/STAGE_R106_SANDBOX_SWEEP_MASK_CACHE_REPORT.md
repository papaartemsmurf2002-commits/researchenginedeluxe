# Stage R106 Sandbox Sweep Mask Cache Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-247-sandbox-sweep-mask-cache.md`
Status: closed

## Summary

WPR106-247 improves sandbox sweep throughput by caching completed
strategy/filter signal masks per prepared market frame. The sandbox no longer
recomputes the same signal/filter mask for every holding-period and exit
variant trial.

## Implementation

- Added a prepared-market signal/filter mask cache in
  `src/tradingbotsuite/research_sandbox/fast_backtest.py`.
- Cache keys are based on signal and filter column/bound inputs, so strategies
  with the same prepared signal/filter requirements can reuse the same mask.
- Cached masks are reused across venues, exit variants, and holding periods
  within the same prepared market frame.
- Missing signal/filter columns and empty 2024+ windows do not build masks;
  they still use the existing blocked-result path.
- Target/stop high/low checks remain per exit variant, preserving existing OHLC
  blocker behavior.
- The change does not alter deterministic trial IDs, score formulas, ranking,
  or result payload boundaries.

## Boundary

This packet changes sandbox sweep efficiency only. It does not alter strategy
math, strict validation, candidate-pack gates, live/paper signals, sizing,
order placement, runtime mode, live configuration, provider downloads, or
promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 70 passed

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

This cache removes repeated signal/filter mask work. Barrier exit scans still
run per trial; a later packet could optimize target/stop path handling if
profiling shows it is the next bottleneck.
