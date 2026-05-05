# WPR21-01 Research Exit Policy Expansion Foundation

Status: closed
Owner: Codex Research Agent
Stage: Stage R21 research exit policy expansion foundation
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Expand the research backtest exit policy foundation beyond fixed holding and lower-timeframe triple barrier while preserving conservative, auditable behavior.

This packet implements primary-bar research exit policies that can be evaluated without live execution or promotion claims. Policies must emit the existing exit artifact fields and fail closed when required context is unavailable.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR21-01-research-exit-policy-expansion-foundation.md`
- `docs/stage_reports/STAGE_R21_RESEARCH_EXIT_POLICY_EXPANSION_FOUNDATION_REPORT.md`
- `src/tradingbotsuite/backtesting/exits.py`
- `src/tradingbotsuite/backtesting/execution_sim.py`
- `src/tradingbotsuite/backtesting/engine.py`
- `src/tradingbotsuite/backtesting/vector_engine.py`
- `tests/backtesting/test_exit_policy_expansion.py`
- `tests/backtesting/test_vector_engine_matches_reference.py`
- `tests/contracts/test_backtest_contracts.py`
- `tests/live/test_preflight.py`
- `tests/unit/test_execution_simulator.py`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No optimistic same-bar stop/target assumptions.
- No lower-timeframe vector sequencing.
- No historical-cycle strategy search changes.
- No candidate acceptance or promotion-ready claims.

## Implementation plan

1. Add a conservative exit-policy dispatcher for primary-bar research policies.
2. Implement auditable foundations for:
   - `volatility_scaled_barrier`;
   - `regime_flip_exit`;
   - `funding_adverse_exit`;
   - `alpha_decay_exit`;
   - `adverse_selection_exit`;
   - `trailing_atr_after_profit`;
   - `max_mae_stop`.
3. Preserve current fixed-holding and lower-timeframe triple-barrier behavior.
4. Keep `VectorBacktestEngine` fixed-holding only and ensure it rejects new policies.
5. Add focused tests for long/short behavior, conservative barrier ordering, missing-context rejection, artifact fields, and vector rejection.

## Exit criteria

- New exit policies produce deterministic `ExitPolicyResult` payloads with existing required fields.
- Missing required context fails clearly for context-dependent exits.
- Existing fixed-holding and triple-barrier tests remain green.
- Vector backend still rejects non-fixed-holding policies.
- Backtest contracts and live preflight pass.

## Closure evidence

- Added a conservative primary-bar research exit dispatcher and foundations for:
  - `volatility_scaled_barrier`;
  - `regime_flip_exit`;
  - `funding_adverse_exit`;
  - `alpha_decay_exit`;
  - `adverse_selection_exit`;
  - `trailing_atr_after_profit`;
  - `max_mae_stop`.
- Added `exit_policy_params` to backtest specs and execution assumptions so policy parameters participate in manifests and cache identity.
- Preserved fixed-holding and lower-timeframe triple-barrier behavior.
- Kept vector backtesting fixed-holding only with explicit rejection coverage for new policies.
- Validation:
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
