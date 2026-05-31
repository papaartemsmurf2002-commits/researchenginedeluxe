# Stage R106 Lower-Timeframe Entry Pricing Report

Date: 2026-05-31

## Scope

WPR106-36 closed `ISSUE-R106-012` for the reference research backtest
simulator. This packet did not add live, paper, order-placement, sizing,
promotion, strategy, filter, or candidate-ready behavior.

## Changes

- Added reference-simulator entry-fill metadata for target fill time, observed
  entry time, primary context bar time, and sequence proof.
- Implemented `lower_timeframe_execution_path` as a lower-timeframe latency
  fill: the first lower-timeframe row at or after
  `decision_time_ms + entry_latency_ms` supplies the entry open price.
- Propagated actual lower-timeframe entry time into holding-window and exit
  timing.
- Made missing lower-timeframe entry `open` or post-latency coverage fail
  closed.
- Preserved vector/CUDA unsupported behavior for lower-timeframe entry sources.
- Added metadata parity for supported primary-bar vector/CUDA outputs.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\unit\test_execution_simulator.py -q
$env:PYTHONPATH='src'; python -m pytest tests\backtesting -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Results:

- Compile passed.
- Execution simulator unit suite: 19 passed.
- Backtesting suite: 124 passed, 1 skipped.
- Contracts: passed after WPR106-36 validation.
- Diff check passed with line-ending warnings only.

## Evidence

- Unit tests prove lower-timeframe entry price differs from primary open and is
  sourced from the lower-timeframe open at the latency fill time.
- Unaligned latency fills use the next lower-timeframe open after the target.
- Missing lower open or missing post-target coverage fails closed.
- Trade rows now include `entry_target_time_ms`,
  `entry_primary_bar_time_ms`, and `entry_sequence_proof`.

## Research Status

No candidate-ready evidence was created. Research outputs remain
`research_only`, `observe_only`, and `promotion_ready: false`.

## Remaining Blockers

- `ISSUE-R106-013`: local credential files can imply Hyperliquid live/testnet
  enablement.
- `ISSUE-R106-014`: runtime artifact validation is not mode-aware and not
  fail-closed for unknown manifests.
