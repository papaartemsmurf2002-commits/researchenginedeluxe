# Stage R106 Sandbox Shared-Market Metric Cache Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-249-sandbox-shared-market-metric-cache.md`
Status: closed

## Summary

WPR106-249 improves shared-market multi-venue sandbox sweep throughput. When a
caller intentionally uses one smoke-test market frame for several venue
descriptors, the sandbox now computes each strategy/filter/exit/holding trial
outcome once and reuses the metrics across those venue rows.

## Implementation

- Added a per-prepared-frame trial metric cache in
  `src/tradingbotsuite/research_sandbox/fast_backtest.py`.
- Cache keys are scoped to the in-memory strategy, filter variant, exit
  variant, and holding period objects in the current prepared market frame.
- The first venue row computes the trial outcome through the existing `_run_one`
  path. Later venue rows copy only the metric/status fields and receive fresh
  deterministic venue-specific trial IDs and venue metadata.
- The existing venue-first loop order is preserved, so tied ranking behavior
  remains stable.
- Descriptor-routed archive sweeps remain one prepared frame per venue
  descriptor; the cache does not collapse distinct venue data.
- The change does not alter deterministic trial identity inputs, score
  formulas, ranking keys, blocker reasons, target/stop behavior, or sandbox
  boundary payloads.

## Boundary

This packet changes sandbox sweep efficiency only. It does not alter strategy
math, strict validation, candidate-pack gates, live/paper signals, sizing,
order placement, runtime mode, live configuration, provider downloads,
descriptor archive loading, or promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 73 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

This packet avoids duplicate trial metric work for shared smoke-test market
frames. Descriptor-routed venue archives still intentionally compute per venue
frame. Barrier exit path scans inside each unique target/stop trial remain a
possible later optimization target if profiling shows they dominate.
