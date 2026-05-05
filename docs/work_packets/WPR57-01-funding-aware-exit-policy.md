# WPR57-01 Funding-Aware Exit Policy

Owner: Codex Research Agent
Status: closed
Stage: R57 funding-aware exit policy
Date opened: 2026-05-05

## Goal

Add a dedicated `funding_aware_exit_v1` research exit policy that can exit before an adverse funding window when projected funding cost is not justified by the current unrealized edge, then include it as an additional checked BTCUSDT and ETHUSDT perp-context-v2 exit policy.

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
docs/work_packets/WPR57-01-funding-aware-exit-policy.md
docs/stage_reports/STAGE_R57_FUNDING_AWARE_EXIT_POLICY_REPORT.md
docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Keep `funding_aware_exit_v1` research-only and primary-bar based.
- Do not model funding payments as cashflows in this packet; the policy only changes exit timing.
- Require observed funding context and time-to-next-funding context; missing columns must fail closed.
- Preserve fixed-holding comparator coverage by keeping `fixed_holding_window` in checked cycles.
- Keep vector backtesting fixed-holding only; `funding_aware_exit_v1` must use or fall back to the reference engine.
- Do not add live execution, promotion readiness, order placement, capital allocation, runtime-control writes, or candidate-pack promotion evidence.

## Policy Semantics

The policy exits a long before a near funding window when positive funding is adverse and expected cost is large relative to unrealized edge. It exits a short when negative funding is adverse under the same rule.

Initial bounded parameters:

```text
funding_threshold
pre_funding_window_h
min_expected_cost_bps
edge_buffer_bps
```

## Validation Plan

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_exit_policy_expansion.py tests\backtesting\test_vector_engine_matches_reference.py tests\contracts\test_backtest_contracts.py tests\contracts\test_research_cycle_contract.py tests\historical\test_full_cycle_local_fixture_pack.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Close Evidence

Record policy behavior, checked-cycle evidence, fail-closed candidate-pack status, touched paths, validation results, and residual risks in `docs/stage_reports/STAGE_R57_FUNDING_AWARE_EXIT_POLICY_REPORT.md`, then close this work packet and ledger row if validation is clean.

Closed 2026-05-05 with validation and cycle evidence recorded in `docs/stage_reports/STAGE_R57_FUNDING_AWARE_EXIT_POLICY_REPORT.md`.
