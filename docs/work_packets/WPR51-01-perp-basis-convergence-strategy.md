# WPR51-01 Perp Basis Convergence Strategy

Owner: Codex Research Agent
Status: closed
Stage: R51 perp basis convergence strategy
Date opened: 2026-05-05

## Goal

Add the first transparent perpetual strategy, `perp_basis_convergence_v2`, using the existing strategy contract and `features_perp_context_v2`.

## Allowed Paths

```text
src/tradingbotsuite/strategies/perp_basis_convergence.py
src/tradingbotsuite/strategies/registry.py
src/tradingbotsuite/strategies/parameters.py
src/tradingbotsuite/strategies/__init__.py
configs/strategies/perp_basis_convergence_v2.json
tests/contracts/test_strategy_contracts.py
tests/integration/test_backtest_engine_fixture.py
tests/historical/
docs/work_packets/WPR51-01-perp-basis-convergence-strategy.md
docs/stage_reports/STAGE_R51_PERP_BASIS_CONVERGENCE_STRATEGY_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Extend the existing `RuleBasedStrategy`/`RuleSignal` pattern.
- `strategy_id = "perp_basis_convergence_v2"`.
- `allowed_holding_periods = ("4h", "12h", "24h", "72h")`.
- `required_feature_sets = ("features_perp_context_v2",)`.
- Use only existing strategy signal columns and contracts.
- Fail closed when required v2 features or quality flags are missing.
- Do not call this arbitrage. It is a single-leg directional convergence proxy.
- Do not add live execution, promotion readiness, order placement, or capital allocation behavior.

## Required Parameters

```text
basis_vol_threshold
premium_z_threshold
min_edge_bps
funding_policy
spacing_bars
```

Optional future parameter `spread_z_max` stays out until book features exist.

## Entry Concept

Long directional convergence proxy:

- basis/premium are sufficiently negative,
- carry-adjusted basis exceeds estimated costs plus minimum edge,
- required context quality is valid.

Short directional convergence proxy:

- basis/premium are sufficiently positive,
- carry-adjusted basis exceeds estimated costs plus minimum edge,
- required context quality is valid.

## Validation Plan

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py tests\integration\test_backtest_engine_fixture.py -q
```

## Close Evidence

Record validation results, touched paths, behavior notes, and any remaining risks in `docs/stage_reports/STAGE_R51_PERP_BASIS_CONVERGENCE_STRATEGY_REPORT.md`, then close this work packet and ledger row if validation is clean.

Closed 2026-05-05 with validation recorded in `docs/stage_reports/STAGE_R51_PERP_BASIS_CONVERGENCE_STRATEGY_REPORT.md`.
