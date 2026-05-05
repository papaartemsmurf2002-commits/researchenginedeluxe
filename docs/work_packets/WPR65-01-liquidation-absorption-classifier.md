# WPR65-01 Liquidation Absorption Classifier

Stage: R65 liquidation absorption classifier
Owner: Codex Research Agent
Status: closed
Created: 2026-05-05

## Goal

Add `liquidation_absorption_classifier_v1` as a research-only transparent
strategy that consumes `features_liquidation_context_v1` and emits standard
strategy signals only when checked liquidation context indicates a large,
directional liquidation window followed by price reclaim/absorption.

## Allowed paths

```text
src/tradingbotsuite/strategies/liquidation_absorption_classifier.py
src/tradingbotsuite/strategies/registry.py
src/tradingbotsuite/strategies/parameters.py
src/tradingbotsuite/strategies/no_trade.py
configs/strategies/liquidation_absorption_classifier_v1.json
tests/contracts/test_strategy_contracts.py
docs/work_packets/WPR65-01-liquidation-absorption-classifier.md
docs/stage_reports/STAGE_R65_LIQUIDATION_ABSORPTION_CLASSIFIER_REPORT.md
docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Do not wire the strategy into checked BTCUSDT or ETHUSDT provider-cycle
  configs in this packet.
- Do not create candidate-pack eligibility, promotion evidence, live signals,
  order placement, runtime writes, or live configuration changes.
- Do not use TradingView exports or synthetic fixture evidence.
- Treat WPR64 Crypto Lake free-sample liquidation fixture evidence as local
  classifier validation only, not broad OOS/stress evidence or performance
  evidence.
- Fail closed when liquidation context is missing, non-finite, latest-window
  only unless explicitly allowed, or not provider-backed.

## Required behavior

- Register `liquidation_absorption_classifier_v1`.
- Require `features_liquidation_context_v1`.
- Add bounded strategy metadata and checked strategy config.
- Add no-trade comparator support for `features_liquidation_context_v1`.
- Emit only standard research-only `RuleSignal` rows.
- Produce long signals after large sell-liquidation pressure plus positive
  absorption reclaim.
- Produce short signals after large buy-liquidation pressure plus positive
  absorption reclaim.
- Add tests for metadata/config loading, signal contract, missing columns,
  fail-closed quality/context checks, invalid parameters, and WPR64 checked
  fixture materialization.

## Exit validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Close evidence

- Added `liquidation_absorption_classifier_v1` as a `RuleBasedStrategy`.
- Registered strategy config:
  `configs/strategies/liquidation_absorption_classifier_v1.json`.
- Added bounded metadata for notional-z, imbalance, reclaim, event-count,
  event-age, latest-window opt-in, and spacing parameters.
- Added no-trade comparator support for `features_liquidation_context_v1`.
- Added contract tests for:
  - registry/config loading,
  - invalid feature/window rejection,
  - metadata coverage,
  - standard research-only signal output,
  - empty `skip_reason` on accepted trade signals,
  - required-column fail-closed behavior,
  - unsafe context fail-closed behavior,
  - invalid-parameter fail-closed behavior,
  - WPR64 checked fixture materialization and classifier execution.
- Checked BTCUSDT/ETHUSDT provider-cycle configs remain unchanged.
- Validation passed:
  - `python -m compileall -q src\tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py -q`
    - 267 passed
  - `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
    - 366 passed
