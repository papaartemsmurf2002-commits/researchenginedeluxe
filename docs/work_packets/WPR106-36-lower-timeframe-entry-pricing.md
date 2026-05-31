# WPR106-36 Lower-Timeframe Entry Pricing

## Goal

Close `ISSUE-R106-012` by making `lower_timeframe_execution_path` use
lower-timeframe rows for latency fill time and fill price in the reference
research backtest simulator, or fail closed when proof is unavailable.

This packet must not add live, paper, order-placement, sizing, promotion, or
candidate-ready behavior.

## Current Repo Facts

- `ExecutionSimulator._validate_assumptions()` requires
  `lower_timeframe_market_data` for `lower_timeframe_execution_path`.
- `_entry_index()` still selects a primary bar from
  `decision_time_ms + entry_latency_ms`.
- `_entry_price()` falls through to primary-bar open for
  `lower_timeframe_execution_path`.
- Exit logic already has lower-timeframe sequence proof for triple-barrier
  exits, but entry semantics do not use that lower frame.
- Vector/CUDA fixed-holding engines already reject or do not support
  `lower_timeframe_execution_path`.

## Conflicts And Stale Docs Found

- Existing tests only prove lower-timeframe entry source requires a lower frame;
  they do not prove the lower frame is used.
- Current historical-cycle backend tests expect vector to reject this source and
  auto backend to fall back to reference. That remains correct.
- Existing lower-timeframe exit tests use rows at or after the entry time; entry
  fill semantics should not weaken those sequence checks.

## Allowed Edit Paths

- `docs/work_packets/WPR106-36-lower-timeframe-entry-pricing.md`
- `docs/work_packets/WPR106-36-progress.jsonl`
- `src/tradingbotsuite/backtesting/execution_sim.py`
- `src/tradingbotsuite/backtesting/engine.py`
- `src/tradingbotsuite/backtesting/vector_engine.py`
- `src/tradingbotsuite/backtesting/cuda_engine.py`
- `src/tradingbotsuite/backtesting/cuda_batched_engine.py`
- `tests/unit/test_execution_simulator.py`
- focused backtesting tests if needed
- `docs/ACTIVE_INDEX.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_LOWER_TIMEFRAME_ENTRY_PRICING_REPORT.md`

## Forbidden Edit Paths

- live/runtime/order-placement modules
- strategy/model/filter implementations
- promotion or candidate-pack gates
- vector/CUDA lower-timeframe support beyond preserving existing fail-closed
  behavior
- data fixtures and generated research artifacts
- `.pytest_cache/**`

## Subagents Used

- Execution Semantics Engineer: inspect current simulator, lower-timeframe
  tests, and smallest safe reference-path fix.

## Tests To Run

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\unit\test_execution_simulator.py -q
$env:PYTHONPATH='src'; python -m pytest tests\backtesting -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Artifacts Expected

- Focused unit tests where primary-open and lower-timeframe fill prices differ.
- Trade metadata proving lower-timeframe entry time, price, and sequence proof.
- Updated issue registry and stage report.

No candidate packs, rankings, live configs, or generated data artifacts are
expected.

## Definition Of Done

- `lower_timeframe_execution_path` selects the first lower-timeframe bar whose
  timestamp is at or after `decision_time_ms + entry_latency_ms`.
- Entry price comes from that lower-timeframe bar's open price.
- Missing lower open/close/timestamp coverage fails closed.
- Trade rows expose enough metadata to prove the target and observed fill time.
- Existing vector/CUDA unsupported behavior is preserved.
- `ISSUE-R106-012` is resolved only after focused validation passes.

## Rollback Plan

Revert only files in the allowed edit paths for this packet. Do not touch live
runtime, generated artifacts, candidate gates, or unrelated cache state.
