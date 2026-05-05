# WPR20-01 Vector Backtest Cycle Integration Benchmark Evidence

Status: closed
Owner: Codex Research Agent
Stage: Stage R20 vector backtest cycle integration benchmark evidence
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Add an opt-in historical research-cycle backend selection for the fixed-holding vector backtest path and produce truthful benchmark evidence. The reference `BacktestEngine` must remain the default.

Vector execution may be used only when the resolved backtest assumptions are inside the WPR19 scope: fixed-holding or fixed-holding alias exits, primary-bar entry sources, primary-close exits, and no lower-timeframe dataset.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR20-01-vector-backtest-cycle-integration-benchmark-evidence.md`
- `docs/stage_reports/STAGE_R20_VECTOR_BACKTEST_CYCLE_INTEGRATION_BENCHMARK_EVIDENCE_REPORT.md`
- `src/tradingbotsuite/research_cycle/spec.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/research_cycle/benchmark.py`
- `src/tradingbotsuite/backtesting/vector_engine.py`
- `tests/backtesting/test_vector_engine_matches_reference.py`
- `tests/contracts/test_backtest_contracts.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `tests/historical/test_research_cycle_benchmark.py`
- `tests/live/test_preflight.py`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No default switch from reference execution to vector execution.
- No vector lower-timeframe or triple-barrier support.
- No acceptance, promotion readiness, or performance claim without benchmark evidence.

## Implementation plan

1. Add a research-cycle spec field for `backtest_backend` with default `reference`.
2. Support `reference`, `vector_fixed_holding`, and conservative `auto` backend modes.
3. Route eligible fixed-holding primary-bar cycle backtests through `VectorBacktestEngine` only when explicitly requested or when `auto` can prove support.
4. Record requested backend, actual backend, fallback/rejection reason, engine version, vector scope, manifest path, result hash, and cache identity in backtest indexes and ranking evidence.
5. Extend benchmark reporting to measure reference vs vector fixed-holding runs without implying production execution-cache reuse.
6. Add tests for default reference behavior, explicit vector use, unsupported fallback/rejection behavior, and benchmark evidence fields.

## Exit criteria

- Historical research-cycle default behavior remains reference engine.
- Explicit vector backend runs supported fixed-holding cycle backtests through `VectorBacktestEngine`.
- Unsupported vector requests fail clearly or fall back only when `auto` is explicitly selected and evidence records the fallback.
- Benchmark evidence reports backend requested/used and separates runtime evidence from unsupported speed claims.
- Contracts, historical tests, backtesting parity tests, and live preflight pass.

## Closure evidence

- Added `backtest_backend` to the historical research-cycle spec with supported values `reference`, `vector_fixed_holding`, and `auto`.
- Kept default cycle execution on `reference`.
- Routed explicit vector-supported aggregate, split, and cost-stress cycle backtests through `VectorBacktestEngine`.
- Added backend requested/used, fallback/rejection reason, engine version, vector scope, and cache identity evidence to rankings, backtest index rows, and cycle manifests.
- Added reference-vs-vector backend comparison to the historical-cycle benchmark report with `speed_claimed: false` and parity/evidence checks instead of a speed gate.
- Validation:
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
