# WPR53-01 Funding Crowding Fade Strategy

Owner: Codex Research Agent
Status: closed
Stage: R53 funding crowding fade strategy
Date opened: 2026-05-05

## Goal

Add the next transparent perpetual strategy, `funding_crowding_fade_v2`, using `features_perp_context_v2`, then include it in the checked BTCUSDT perp-context-v2 research cycle.

## Allowed Paths

```text
src/tradingbotsuite/strategies/funding_crowding_fade.py
src/tradingbotsuite/strategies/registry.py
src/tradingbotsuite/strategies/parameters.py
configs/strategies/funding_crowding_fade_v2.json
configs/research/full_cycle_btcusdt_perp_context_v2.json
tests/contracts/test_strategy_contracts.py
tests/integration/test_backtest_engine_fixture.py
tests/historical/test_full_cycle_local_fixture_pack.py
docs/work_packets/WPR53-01-funding-crowding-fade-strategy.md
docs/stage_reports/STAGE_R53_FUNDING_CROWDING_FADE_STRATEGY_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Extend the existing `RuleBasedStrategy`/`RuleSignal` pattern.
- `strategy_id = "funding_crowding_fade_v2"`.
- Use only `features_perp_context_v2`.
- Use only existing strategy signal columns and contracts.
- Fail closed when required funding, premium/basis, OI, or quality context is missing or non-finite.
- Do not call this arbitrage. It is a single-leg directional crowding fade proxy.
- Do not add live execution, promotion readiness, order placement, or capital allocation behavior.
- Do not add liquidation, L2, cross-exchange, or multi-symbol requirements.

## Required Parameters

```text
funding_z_threshold
funding_rate_abs_bps_threshold
premium_confirmation_bps
min_edge_bps
oi_confirmation_z_min
funding_momentum_policy
spacing_bars
```

## Entry Concept

Long directional crowding fade proxy:

- funding is sufficiently negative and statistically stretched,
- premium/basis confirms short-side crowding,
- OI confirmation is non-adverse,
- estimated funding reversion edge exceeds the minimum edge,
- required context quality is valid.

Short directional crowding fade proxy:

- funding is sufficiently positive and statistically stretched,
- premium/basis confirms long-side crowding,
- OI confirmation is non-adverse,
- estimated funding reversion edge exceeds the minimum edge,
- required context quality is valid.

## Validation Plan

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py tests\integration\test_backtest_engine_fixture.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\historical\test_full_cycle_local_fixture_pack.py -q
```

## Close Evidence

Record validation results, touched paths, behavior notes, cycle outcome, and any remaining risks in `docs/stage_reports/STAGE_R53_FUNDING_CROWDING_FADE_STRATEGY_REPORT.md`, then close this work packet and ledger row if validation is clean.

Closed 2026-05-05 with validation and cycle evidence recorded in `docs/stage_reports/STAGE_R53_FUNDING_CROWDING_FADE_STRATEGY_REPORT.md`.
