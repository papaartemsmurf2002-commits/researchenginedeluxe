# WPR54-01 OI Flow Breakout Strategy

Owner: Codex Research Agent
Status: closed
Stage: R54 OI flow breakout strategy
Date opened: 2026-05-05

## Goal

Add the next transparent perpetual strategy, `oi_flow_breakout_v2`, using `features_perp_context_v2`, then include it in the checked BTCUSDT perp-context-v2 research cycle.

## Allowed Paths

```text
src/tradingbotsuite/strategies/oi_flow_breakout.py
src/tradingbotsuite/strategies/registry.py
src/tradingbotsuite/strategies/parameters.py
configs/strategies/oi_flow_breakout_v2.json
configs/research/full_cycle_btcusdt_perp_context_v2.json
data/research/historical_cycles/btcusdt_perp_context_v2_foundation/**
tests/contracts/test_strategy_contracts.py
tests/contracts/test_research_cycle_contract.py
tests/integration/test_backtest_engine_fixture.py
tests/historical/test_full_cycle_local_fixture_pack.py
docs/work_packets/WPR54-01-oi-flow-breakout-strategy.md
docs/stage_reports/STAGE_R54_OI_FLOW_BREAKOUT_STRATEGY_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Extend the existing `RuleBasedStrategy`/`RuleSignal` pattern.
- `strategy_id = "oi_flow_breakout_v2"`.
- Use only `features_perp_context_v2`.
- Use only existing strategy signal columns and contracts.
- Interpret "breakout" as an OI/premium expansion proxy because `features_perp_context_v2` is a context-only feature set.
- Fail closed when required OI, premium/basis, or quality context is missing or non-finite.
- Treat flow as optional confirmation while the checked durable BTCUSDT fixture omits `agg_trade`; missing flow must remain unavailable, not zero.
- Do not regenerate checked fixture data in this packet.
- Do not add live execution, promotion readiness, order placement, or capital allocation behavior.
- Do not add liquidation, L2, cross-exchange, multi-symbol, or price-path feature requirements.

## Required Parameters

```text
oi_delta_z_threshold
oi_delta_min_notional
premium_confirmation_bps
premium_slope_min_bps
flow_z_threshold
flow_confirmation_policy
spacing_bars
```

## Entry Concept

Long directional OI expansion proxy:

- OI delta is statistically expanded and positive,
- premium/basis confirms upside participation,
- premium slope is non-adverse if required,
- flow confirms the direction when available and configured,
- required context quality is valid.

Short directional OI expansion proxy:

- OI delta is statistically expanded and positive,
- premium/basis confirms downside participation,
- premium slope is non-adverse if required,
- flow confirms the direction when available and configured,
- required context quality is valid.

## Validation Plan

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py tests\integration\test_backtest_engine_fixture.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\historical\test_full_cycle_local_fixture_pack.py -q
```

## Close Evidence

Record validation results, touched paths, behavior notes, cycle outcome, and any remaining risks in `docs/stage_reports/STAGE_R54_OI_FLOW_BREAKOUT_STRATEGY_REPORT.md`, then close this work packet and ledger row if validation is clean.

Closed 2026-05-05 with validation and cycle evidence recorded in `docs/stage_reports/STAGE_R54_OI_FLOW_BREAKOUT_STRATEGY_REPORT.md`.
