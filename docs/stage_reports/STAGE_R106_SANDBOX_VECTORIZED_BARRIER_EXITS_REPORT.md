# Stage R106 Sandbox Vectorized Barrier Exits Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-250-sandbox-vectorized-barrier-exits.md`
Status: closed

## Summary

WPR106-250 improves target/stop exit sweep throughput by replacing nested
per-trade/per-bar barrier scans with a vectorized primary-bar window
calculation.

## Implementation

- Refactored `_barrier_exit_prices()` in
  `src/tradingbotsuite/research_sandbox/fast_backtest.py`.
- The function now builds a NumPy matrix of primary-bar window indexes for each
  trial, masks bars outside each trade's holding window, and computes target
  and stop hits with vectorized comparisons.
- Target-only and stop-only exits select the first barrier hit for each trade.
- Conservative target/stop exits compare first target and first stop offsets
  and select stop when both occur on the same bar, preserving stop-first
  ambiguity handling.
- No-hit target/stop exits still fall back to the fixed-hold close.
- Missing high/low columns still block before barrier pricing, preserving
  fail-closed OHLC behavior.
- The change does not alter deterministic trial identity inputs, score
  formulas, ranking keys, blocker reasons, or sandbox boundary payloads.

## Boundary

This packet changes sandbox sweep efficiency only. It does not alter strategy
math, strict validation, candidate-pack gates, live/paper signals, sizing,
order placement, runtime mode, live configuration, provider downloads,
descriptor archive loading, or promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 75 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

The sandbox fixed-hold and primary-bar target/stop paths now avoid the largest
obvious Python-loop costs in the sweep layer. Later throughput work should be
guided by profiling full archive-backed sandbox iterations rather than by
guessing from code shape alone.
