# V2 Strategy Spec Contract

Status: v2 Phase 10 declarative spec contract
Audit ID: `V2-AUD-STRAT-001`

## Purpose

Declarative strategy specs are the first-class v2 strategy interface.

## Schema Names

- `StrategySpec`
- `StrategySpecValidationResult`
- `MarketScope`
- `StrategyInputs`
- `StrategyLogic`
- `RiskConfig`
- `ExecutionConfig`
- `StrategyValidationConfig`
- `SignalFrame`
- `SignalRow`

## Required Rules

- Specs must declare schema version, strategy family, inputs, logic, risk,
  execution costs, validation policy, and boundary metadata.
- Validation rejects arbitrary Python, network access, secrets, filesystem
  escapes, live/order/sizing/runtime imports, and unknown schema keys.
- Spec hash is part of run identity.
- Declarative specs use `schema_version: strategy_spec_v1`.
- Inputs must use registered fields only.
- Logic must use registered signal types, rank metrics, and filters only.
- The Phase 10 registry includes:
  - cross-sectional rank;
  - mean reversion;
  - funding carry;
  - volatility breakout;
  - liquidity-filtered momentum.
- Execution declarations must include supported `price_basis`, `fee_model`,
  and `slippage_model`.
- Validation declarations must keep `exclude_lockbox: true`, earliest start on
  or after 2024-01-01, and `universe_mode: as_of` for accepted/reported
  evidence.
- The compile helper may compile a validated declarative spec over an
  in-memory panel into a deterministic research-only `SignalFrame`.
- Signal-frame compilation must not read files, fetch network data, execute
  Python strategy code, place orders, mutate runtime mode, or run a backtest.
- Built-in examples must validate for at least cross-sectional momentum, mean
  reversion, and funding/carry; Phase 10 also includes volatility breakout and
  liquidity-filtered momentum examples.

## Forbidden

- Agent-provided arbitrary Python as the default strategy path.
- Live/paper/order/sizing implications.
- Current-universe accepted/reported evidence.
- Lockbox access for ordinary strategy iteration.
- URLs, file paths, secret/credential references, shell/subprocess/socket
  access, or hidden side-effect fields inside declarative specs.
- Unknown schema keys or unsupported indicator/expression names.
- Missing cost or slippage declarations.
