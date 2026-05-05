# WPR62-01 Liquidation Fixture Intake Foundation

Owner: Codex Research Agent
Status: closed
Stage: R62 liquidation fixture intake foundation
Date opened: 2026-05-05

## Goal

Add the durable research-only foundation needed before `liquidation_absorption_classifier_v1` can be designed. This packet makes liquidation archive rows ingestible through the existing provider archive path and materializable as an optional historical fixture-pack context family.

## Allowed Paths

```text
src/tradingbotsuite/research/market_data.py
src/tradingbotsuite/data/historical_fixture_pack.py
src/tradingbotsuite/main.py
tests/tradingbotsuite/test_market_data_collection.py
tests/contracts/test_historical_fixture_pack_contract.py
docs/work_packets/WPR62-01-liquidation-fixture-intake-foundation.md
docs/stage_reports/STAGE_R62_LIQUIDATION_FIXTURE_INTAKE_FOUNDATION_REPORT.md
docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Keep all outputs research-only, observe-only, and promotion-ready false.
- Do not implement `liquidation_absorption_classifier_v1` in this packet.
- Do not add live, paper, shadow, testnet, canary, or promotion workflow behavior.
- Do not add provider credentials, paid Crypto Lake access, AWS profile setup, or secret material.
- Do not treat missing liquidation windows as zero-liquidation windows.
- Do not wire liquidation context into checked provider-cycle configs.
- Do not change holding-window, optimizer, candidate-pack, or live preflight semantics.

## Required Behavior

- Allow Crypto Lake free-sample/local-export ingestion for `liquidation` rows.
- Normalize liquidation rows into the existing archive contract:
  - `event_time_ms`
  - `symbol`
  - `side`
  - `price`
  - `quantity`
  - optional `average_price`, `order_status`, `last_filled_quantity`, `trade_time_ms`, `order_type`, `time_in_force`
- Preserve receive-time and provider-mismatch metadata when supplied.
- Mark liquidation archive manifests as `perp_context` with diagnostic-only retention/coverage metadata.
- Allow `liquidation` as an optional historical fixture-pack context family from local provider manifests.
- Aggregate duplicate same-timestamp liquidation events into deterministic fixture rows with count, notional, side notional, and side-imbalance columns.
- Keep unknown stream/archive windows represented by absence and quality metadata, never zero-filled synthetic context.

## Validation Plan

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py tests\contracts\test_historical_fixture_pack_contract.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Close Evidence

Record implemented intake/materialization behavior, focused validation, unchanged classifier/cycle/live boundaries, and residual risks in `docs/stage_reports/STAGE_R62_LIQUIDATION_FIXTURE_INTAKE_FOUNDATION_REPORT.md`, then close this packet and update the ledger.

Closed 2026-05-05 with validation and boundary evidence recorded in `docs/stage_reports/STAGE_R62_LIQUIDATION_FIXTURE_INTAKE_FOUNDATION_REPORT.md`.
