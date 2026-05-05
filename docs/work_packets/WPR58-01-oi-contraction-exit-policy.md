# WPR58-01 OI Contraction Exit Policy

Owner: Codex Research Agent
Status: closed
Stage: R58 OI contraction exit policy
Date opened: 2026-05-05

## Goal

Add a dedicated `oi_contraction_exit_v1` research exit policy that can exit a primary-bar research trade when open-interest contraction indicates momentum decay and the current unrealized edge is not large enough to justify staying in the position. Include it as an additional checked BTCUSDT and ETHUSDT perp-context-v2 exit policy.

## Allowed Paths

```text
src/tradingbotsuite/backtesting/exits.py
src/tradingbotsuite/backtesting/execution_sim.py
src/tradingbotsuite/backtesting/engine.py
src/tradingbotsuite/research_cycle/spec.py
configs/research/full_cycle_btcusdt_perp_context_v2.json
configs/research/full_cycle_ethusdt_perp_context_v2.json
data/research/historical_cycles/btcusdt_perp_context_v2_foundation/**
data/research/historical_cycles/ethusdt_perp_context_v2_foundation/**
tests/backtesting/test_exit_policy_expansion.py
tests/backtesting/test_vector_engine_matches_reference.py
tests/contracts/test_backtest_contracts.py
tests/contracts/test_research_cycle_contract.py
tests/historical/test_full_cycle_local_fixture_pack.py
docs/work_packets/WPR58-01-oi-contraction-exit-policy.md
docs/stage_reports/STAGE_R58_OI_CONTRACTION_EXIT_POLICY_REPORT.md
docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Keep `oi_contraction_exit_v1` research-only and primary-bar based.
- Use existing `features_perp_context_v2` OI columns; do not add a new data family.
- Require observed OI delta and OI quality context; missing columns must fail closed.
- Preserve fixed-holding and funding-aware comparator coverage in checked cycles.
- Keep vector backtesting fixed-holding only; `oi_contraction_exit_v1` must use or fall back to the reference engine.
- Do not add live execution, promotion readiness, order placement, capital allocation, runtime-control writes, or candidate-pack promotion evidence.

## Policy Semantics

The policy exits when strong OI contraction suggests momentum decay and the current trade does not have enough unrealized edge to override that warning.

Initial bounded parameters:

```text
oi_delta_z_threshold
min_oi_delta_abs
max_unrealized_edge_bps
```

Initial required columns:

```text
oi_notional
oi_delta_1h
oi_delta_z_7d
quality_has_oi_gap
```

## Validation Plan

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_exit_policy_expansion.py tests\backtesting\test_vector_engine_matches_reference.py tests\contracts\test_backtest_contracts.py tests\contracts\test_research_cycle_contract.py tests\historical\test_full_cycle_local_fixture_pack.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Close Evidence

Record policy behavior, checked-cycle evidence, fail-closed candidate-pack status, touched paths, validation results, and residual risks in `docs/stage_reports/STAGE_R58_OI_CONTRACTION_EXIT_POLICY_REPORT.md`, then close this work packet and ledger row if validation is clean.

Closed 2026-05-05 with validation and cycle evidence recorded in `docs/stage_reports/STAGE_R58_OI_CONTRACTION_EXIT_POLICY_REPORT.md`.
