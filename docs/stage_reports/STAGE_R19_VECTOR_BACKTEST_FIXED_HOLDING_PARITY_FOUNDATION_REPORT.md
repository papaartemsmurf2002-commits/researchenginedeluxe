# Stage R19 Vector Backtest Fixed Holding Parity Foundation Report

Date: 2026-05-04
Owner: Codex Research Agent
Status: closed

## Scope

WPR19 added a conservative vector-oriented backtest path for research-only fixed-holding, primary-bar assumptions. The reference `BacktestEngine` remains the default runner path.

## Completed

- Added `src/tradingbotsuite/backtesting/vector_engine.py`.
- Exported `VectorBacktestEngine` and `VECTOR_BACKTEST_ENGINE_VERSION`.
- Reused the reference data loading, strategy signal validation, execution assumption validation, metrics, artifact writing shape, and research-only manifest fields.
- Added explicit rejection for unsupported vector scopes:
  - lower-timeframe dataset paths;
  - lower-timeframe entry sources;
  - lower-timeframe exit sequencing;
  - non-fixed-holding exit policies.
- Preserved fixed-holding alias parity for `*_time_exit` policies.
- Added vector-specific config and cache-key identity fields in vector manifests.

## Parity Evidence

`tests/backtesting/test_vector_engine_matches_reference.py` verifies that vector output matches the reference engine for:

- trades;
- signals;
- equity curves;
- metrics;
- fixed-holding aliases;
- no-trade/empty-trade paths across all supported holding windows;
- end-of-data fixed-holding fallback;
- invalid reference assumption validation.

## Validation

- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/backtesting/test_vector_engine_matches_reference.py -q` (`8 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_backtest_contracts.py -q` (`10 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q` (`24 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` (`59 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/backtesting -q` (`21 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/historical -q` (`10 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite -q` (`273 passed`)
- `git diff --check` passed with line-ending warnings only.

## Boundary Notes

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital-allocation behavior was added.
- Vector execution is not yet integrated into the historical research-cycle runner.
- No speed claim is made in this stage; benchmark evidence belongs to a later opt-in integration packet.
