# WPR63-01 Liquidation Context Feature Pack

Owner: Codex Research Agent
Status: closed
Stage: R63 liquidation context feature pack
Date opened: 2026-05-05

## Goal

Add a registered research-only liquidation context feature set that consumes optional liquidation fixture context created by WPR62. This packet turns event-only liquidation rows into conservative point-in-time feature columns without implying that missing liquidation windows are zero.

## Allowed Paths

```text
src/tradingbotsuite/features/registry.py
src/tradingbotsuite/features/packs.py
src/tradingbotsuite/features/builders.py
src/tradingbotsuite/features/cache.py
configs/features/features_liquidation_context_v1.json
tests/features/test_feature_builders.py
tests/contracts/test_feature_contracts.py
docs/work_packets/WPR63-01-liquidation-context-feature-pack.md
docs/stage_reports/STAGE_R63_LIQUIDATION_CONTEXT_FEATURE_PACK_REPORT.md
docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Keep all outputs research-only, observe-only, and promotion-ready false.
- Do not implement `liquidation_absorption_classifier_v1` in this packet.
- Do not add checked BTCUSDT/ETHUSDT provider-cycle wiring.
- Do not use TradingView or legacy chart exports.
- Do not zero-fill unknown liquidation windows.
- Do not change candidate-pack gates, optimizer behavior, holding-window semantics, live preflight, or promotion behavior.

## Required Behavior

- Register `features_liquidation_context_v1` backed by a `liquidation_context_v1` feature pack.
- Materialize optional `liquidation` fixture context with event-window semantics, not backward-as-of carry-forward.
- Produce point-in-time liquidation features:
  - `liq_event_count_1h`
  - `liq_total_notional_1h`
  - `liq_buy_notional_1h`
  - `liq_sell_notional_1h`
  - `liq_net_notional_1h`
  - `liq_imbalance_ratio_1h`
  - `liq_total_notional_z_7d`
  - `liq_time_since_last_event_h`
  - `liq_absorption_reclaim_bps`
  - `quality_has_liquidation_gap`
  - `quality_liquidation_provider_backed`
  - `quality_liquidation_latest_window_context_only`
- Preserve explicit missingness and availability columns for every liquidation feature.
- Ensure feature-cache identity changes when liquidation fixture context changes.

## Validation Plan

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_feature_contracts.py tests\features -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Close Evidence

Record feature semantics, no-lookahead behavior, missing-window handling, focused validation, and unchanged classifier/live boundaries in `docs/stage_reports/STAGE_R63_LIQUIDATION_CONTEXT_FEATURE_PACK_REPORT.md`, then close this packet and update the ledger.

Closed 2026-05-05 with validation and boundary evidence recorded in `docs/stage_reports/STAGE_R63_LIQUIDATION_CONTEXT_FEATURE_PACK_REPORT.md`.
