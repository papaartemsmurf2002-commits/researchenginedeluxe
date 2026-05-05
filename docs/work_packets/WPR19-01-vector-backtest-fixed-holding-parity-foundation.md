# WPR19-01 Vector Backtest Fixed Holding Parity Foundation

Status: closed
Owner: Codex Research Agent
Stage: Stage R19 vector backtest fixed-holding parity foundation
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Add a conservative vector backtest engine foundation for fixed-holding, primary-bar research backtests and prove parity against the existing reference `BacktestEngine` for supported assumptions.

This is the first vector-speed-path step from the plan. It must remain research-only and must not replace the reference engine in the historical-cycle runner until parity and benchmark evidence are broader.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR19-01-vector-backtest-fixed-holding-parity-foundation.md`
- `docs/stage_reports/STAGE_R19_VECTOR_BACKTEST_FIXED_HOLDING_PARITY_FOUNDATION_REPORT.md`
- `src/tradingbotsuite/backtesting/vector_engine.py`
- `src/tradingbotsuite/backtesting/__init__.py`
- `tests/backtesting/test_vector_engine_matches_reference.py`
- `tests/contracts/test_backtest_contracts.py`
- `tests/live/test_preflight.py`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No lower-timeframe vector sequencing.
- No triple-barrier/vector exit rewrite in this packet.
- No historical-cycle runner switch to vector execution.

## Implementation plan

1. Add `VectorBacktestEngine` for fixed holding windows, primary-close exits, and primary-bar entry prices.
2. Reuse existing strategy signal validation, metrics, manifests, and research-only artifact contracts.
3. Reject unsupported vector assumptions explicitly.
4. Add parity tests comparing vector trades and metrics against `BacktestEngine`.
5. Export the vector engine without changing default runner behavior.

## Exit criteria

- Vector engine writes the same artifact family as the reference engine.
- Vector trades, signals, equity curves, and metrics match the reference engine for fixed-holding primary-bar cases.
- Fixed-holding aliases, no-trade cases, all supported holding windows, and end-of-data fallback parity are covered.
- Unsupported lower-timeframe/triple-barrier assumptions fail clearly.
- Existing backtest contracts and live preflight still pass.

## Closure evidence

- Added `VectorBacktestEngine` and `VECTOR_BACKTEST_ENGINE_VERSION` exports.
- Vector execution is scoped to primary-bar fixed-holding exits and writes research-only/observe-only/promotion-blocked artifacts.
- Vector manifests record the reference engine version, vector execution scope, vector config identity, and vector cache-key identity.
- Unsupported lower-timeframe entry/exit assumptions and non-fixed-holding exits reject explicitly.
- Validation:
  - `python -m compileall -q src/tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests/backtesting/test_vector_engine_matches_reference.py -q` (`8 passed`)
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_backtest_contracts.py -q` (`10 passed`)
  - `$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q` (`24 passed`)
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` (`59 passed`)
  - `$env:PYTHONPATH='src'; python -m pytest tests/backtesting -q` (`21 passed`)
  - `$env:PYTHONPATH='src'; python -m pytest tests/historical -q` (`10 passed`)
  - `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite -q` (`273 passed`)
  - `git diff --check` passed with line-ending warnings only.
