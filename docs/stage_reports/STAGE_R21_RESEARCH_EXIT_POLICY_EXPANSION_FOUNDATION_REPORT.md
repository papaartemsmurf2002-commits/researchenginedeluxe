# Stage R21 Research Exit Policy Expansion Foundation Report

Date: 2026-05-04
Owner: Codex Research Agent
Status: closed

## Scope

WPR21 expanded the research backtest exit-policy foundation with conservative primary-bar policies. The work remains historical research only and does not change live, promotion, or vector lower-timeframe behavior.

## Completed

- Added primary-bar research exit-policy dispatch in the execution simulator.
- Added policy implementations for:
  - `volatility_scaled_barrier`;
  - `regime_flip_exit`;
  - `funding_adverse_exit`;
  - `alpha_decay_exit`;
  - `adverse_selection_exit`;
  - `trailing_atr_after_profit`;
  - `max_mae_stop`.
- Added `exit_policy_params` to `BacktestSpec` and `ExecutionAssumptions`.
- Preserved manifest/cache identity for exit-policy parameters.
- Preserved fixed-holding and lower-timeframe triple-barrier behavior.
- Kept `VectorBacktestEngine` scoped to fixed-holding primary-bar parity only.

## Validation

- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/backtesting -q` (`43 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/unit/test_execution_simulator.py -q` (`16 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_backtest_contracts.py -q` (`12 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q` (`24 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` (`65 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/historical -q` (`12 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/research_artifacts -q` (`23 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite -q` (`273 passed`)
- `git diff --check` passed with line-ending warnings only.

## Boundary Notes

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital-allocation behavior was added.
- Primary-bar policies are conservative research foundations and do not replace lower-timeframe sequencing where exact intrabar ordering is required.
- Vector execution still rejects every non-fixed-holding policy.
