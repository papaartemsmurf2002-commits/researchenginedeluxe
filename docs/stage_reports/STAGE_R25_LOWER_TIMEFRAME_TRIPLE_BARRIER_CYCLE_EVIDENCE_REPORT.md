# Stage R25 Lower-Timeframe Triple-Barrier Cycle Evidence Report

Date: 2026-05-04
Owner: Codex Research Agent
Status: closed

## Scope

Stage R25 exposed fixture-backed lower-timeframe triple-barrier exits as explicit historical research-cycle candidate policies, with provenance and fail-closed behavior.

No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work was performed. All artifacts remain research-only, observe-only, and not promotion-ready.

## Changes

- Added `data.lower_timeframe_dataset_path` to historical cycle specs and resolved spec payloads.
- Added fixture-pack validation support for strict `lower_timeframe_bars` OHLC sequence families.
- Added `triple_barrier` and `triple_barrier_atr` to supported research-cycle exit policies with positive `target_return` and `stop_return` requirements.
- Routed lower-timeframe datasets into aggregate, validation split, and cost-stress backtests for lower-timeframe exit-policy candidates only.
- Recorded lower-timeframe path, hash, cache-key component, exit price source, sequence-use status, sequence proof counts, and barrier-hit counts in cycle artifacts.
- Added early fail-closed checks for missing or invalid lower-timeframe datasets.
- Preserved vector boundaries: vector lower-timeframe execution remains unsupported; `auto` falls back to reference execution with fallback reasons recorded.

## Validation

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_historical_fixture_pack_contract.py tests/contracts/test_research_cycle_contract.py tests/backtesting/test_vector_engine_matches_reference.py tests/historical/test_full_cycle_local_fixture_pack.py tests/historical/test_full_cycle_synthetic.py tests/live/test_preflight.py -q
git diff --check
```

Results:

- Compile: passed.
- Contracts: 75 passed.
- WPR25 packet tests: 85 passed.
- `git diff --check`: line-ending warnings only.

## Decision

Stage R25 is closed. Lower-timeframe triple-barrier cycles now produce auditable research evidence without changing fixed-holding defaults or vector execution scope.
