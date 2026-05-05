# Stage R20 Vector Backtest Cycle Integration Benchmark Evidence Report

Date: 2026-05-04
Owner: Codex Research Agent
Status: closed

## Scope

WPR20 added opt-in vector backend routing to the historical research cycle while keeping the reference backtest engine as the default.

## Completed

- Added `backtest_backend` to `HistoricalResearchCycleSpec`.
- Supported backend modes:
  - `reference`: always uses `BacktestEngine`;
  - `vector_fixed_holding`: uses `VectorBacktestEngine` only when the resolved `BacktestSpec` is supported;
  - `auto`: uses vector for supported fixed-holding primary-bar specs and falls back to reference with a recorded reason otherwise.
- Added backend evidence to:
  - `candidate_rankings.parquet`;
  - `backtest_index.parquet`;
  - `research_cycle_manifest.json`;
  - benchmark reports.
- Added explicit vector cycle tests and unsupported vector fallback/fail-closed tests.
- Added a benchmark `reference_vs_vector_backend_comparison` section that reports behavioral parity and runtime observations without claiming general speedup.

## Boundary Notes

- Reference execution remains the default.
- Vector execution remains scoped to fixed-holding primary-bar research backtests.
- Triple-barrier and lower-timeframe vector support remain unsupported.
- Benchmark runtime ratios are observations only; no production speed or promotion claim is made.
- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital-allocation behavior was added.

## Validation

- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/backtesting/test_vector_engine_matches_reference.py -q` (`8 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_backtest_contracts.py tests/contracts/test_research_cycle_contract.py -q` (`25 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` (`63 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/historical/test_full_cycle_synthetic.py -q` (`6 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/historical/test_research_cycle_benchmark.py -q` (`4 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/historical -q` (`12 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/backtesting -q` (`21 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/research_artifacts -q` (`23 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q` (`24 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite -q` (`273 passed`)
- `git diff --check` passed with line-ending warnings only.
