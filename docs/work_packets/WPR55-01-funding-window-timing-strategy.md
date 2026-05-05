# WPR55-01 Funding Window Timing Strategy

Owner: Codex Research Agent
Status: closed
Stage: R55 funding window timing strategy
Date opened: 2026-05-05

## Goal

Add the next transparent perpetual strategy, `funding_window_timing_v1`, using `features_perp_context_v2`, then include it in the checked BTCUSDT perp-context-v2 research cycle.

## Allowed Paths

```text
src/tradingbotsuite/strategies/funding_window_timing.py
src/tradingbotsuite/strategies/registry.py
src/tradingbotsuite/strategies/parameters.py
configs/strategies/funding_window_timing_v1.json
configs/research/full_cycle_btcusdt_perp_context_v2.json
data/research/historical_cycles/btcusdt_perp_context_v2_foundation/**
tests/contracts/test_strategy_contracts.py
tests/contracts/test_research_cycle_contract.py
tests/integration/test_backtest_engine_fixture.py
tests/historical/test_full_cycle_local_fixture_pack.py
docs/work_packets/WPR55-01-funding-window-timing-strategy.md
docs/stage_reports/STAGE_R55_FUNDING_WINDOW_TIMING_STRATEGY_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Extend the existing `RuleBasedStrategy`/`RuleSignal` pattern.
- `strategy_id = "funding_window_timing_v1"`.
- Use only `features_perp_context_v2`.
- Use only existing strategy signal columns and contracts.
- Treat the strategy as a single-leg directional timing proxy around funding windows.
- Do not model funding payments as backtest cashflows in this packet; any funding effect remains signal context only.
- Fail closed when required funding, premium/basis, timing, or quality context is missing or non-finite.
- Do not regenerate checked fixture data in this packet.
- Do not add live execution, promotion readiness, order placement, or capital allocation behavior.
- Do not add funding cap/floor/interval-row, liquidation, L2, cross-exchange, multi-symbol, or new exit-policy requirements.

## Required Parameters

```text
funding_z_threshold
funding_rate_abs_bps_threshold
premium_confirmation_bps
entry_window_h
window_mode
funding_momentum_policy
oi_confirmation_z_min
spacing_bars
```

## Entry Concept

Post-funding reversion proxy:

- bar is inside the configured post-settlement funding window,
- funding is statistically and absolutely stretched,
- premium/basis confirms the crowded side,
- funding momentum is non-adverse under the configured policy,
- OI confirmation is non-adverse when required,
- required context quality is valid.

Pre-funding fade proxy:

- bar is inside the configured pre-settlement funding window,
- funding and premium/basis confirm crowding,
- the same momentum, OI, and quality gates pass.

## Validation Plan

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py tests\integration\test_backtest_engine_fixture.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\historical\test_full_cycle_local_fixture_pack.py -q
```

## Close Evidence

Record validation results, touched paths, behavior notes, cycle outcome, and any remaining risks in `docs/stage_reports/STAGE_R55_FUNDING_WINDOW_TIMING_STRATEGY_REPORT.md`, then close this work packet and ledger row if validation is clean.

Closed 2026-05-05 with validation and cycle evidence recorded in `docs/stage_reports/STAGE_R55_FUNDING_WINDOW_TIMING_STRATEGY_REPORT.md`.
