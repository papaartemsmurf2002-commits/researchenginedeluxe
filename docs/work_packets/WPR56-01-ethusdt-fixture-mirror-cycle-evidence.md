# WPR56-01 ETHUSDT Fixture Mirror Cycle Evidence

Owner: Codex Research Agent
Status: closed
Stage: R56 ETHUSDT fixture mirror cycle evidence
Date opened: 2026-05-05

## Goal

Create a durable ETHUSDT provider-backed perp-context-v2 fixture pack and a checked mirror cycle spec that matches the current BTCUSDT research cycle structure.

## Allowed Paths

```text
.gitignore
configs/research/full_cycle_ethusdt_perp_context_v2.json
data/research/market_data/binance_usdm/wpr56_ethusdt_latest_month_context_provider_v1/**
data/research/fixtures/ethusdt_context_provider_latest_month_v1/**
data/research/historical_cycles/ethusdt_perp_context_v2_foundation/**
src/tradingbotsuite/data/historical_fixture_pack.py
src/tradingbotsuite/features/builders.py
src/tradingbotsuite/research/market_data.py
tests/contracts/test_historical_fixture_pack_contract.py
tests/features/test_feature_builders.py
tests/historical/test_full_cycle_local_fixture_pack.py
tests/tradingbotsuite/test_market_data_collection.py
docs/work_packets/WPR56-01-ethusdt-fixture-mirror-cycle-evidence.md
docs/stage_reports/STAGE_R56_ETHUSDT_FIXTURE_MIRROR_CYCLE_EVIDENCE_REPORT.md
docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Use only provider-backed Binance USD-M public data already supported by repo collectors.
- Do not use TradingView exports or legacy chart artifacts.
- Keep raw REST collection cache local unless explicitly needed for provenance; check in only the compact durable fixture pack.
- If Binance endpoint behavior blocks ETH collection, fix the collector in place with focused regression tests instead of bypassing normalized manifests.
- Preserve fixture-family latest-window provenance through fixture validation and feature materialization so retention-limited provider context stays visible to strategies and evidence.
- Preserve `research_only: true`, `observe_only: true`, and `promotion_ready: false`.
- Keep all generated evidence latest-window only; do not describe it as OOS acceptance, multi-year stress evidence, or promotion evidence.
- Do not add live execution, order placement, capital allocation, runtime-control writes, or promotion readiness.
- Do not change the single-symbol cycle spec shape.
- Do not add ETH/BTC cross-asset strategy behavior in this packet.

## Required Fixture Scope

Target the current BTCUSDT provider latest-month fixture window, then trim only as required to keep all ETHUSDT context families complete under Binance direct-endpoint retention:

```text
Bars, premium index, open interest:
2026-04-05T00:00:00Z through 2026-05-04T22:00:00Z
1775347200000 through 1777932000000

Funding:
2026-04-04T16:00:00Z through 2026-05-04T22:00:00Z
1775318400000 through 1777932000000
```

If the Binance open-interest endpoint rejects the oldest mirror-window rows because of retention, use the maximal zero-gap ETHUSDT tail shared by 15m bars, premium index, open interest, and funding context. Record the exact retained first timestamp in the stage report.

Required families:

- `bars` from 15m Binance USD-M klines.
- `funding_rate`.
- `premium_index`.
- `open_interest`.

Omit `agg_trade` and `lower_timeframe_bars` unless a later packet supplies durable data.

## Required Cycle Scope

Add `configs/research/full_cycle_ethusdt_perp_context_v2.json` with:

- `cycle_id = "ethusdt-perp-context-v2-foundation"`.
- `symbol = "ETHUSDT"`.
- `features.feature_sets = ["features_perp_context_v2"]`.
- Holding windows: `4h`, `12h`, `24h`, `72h`.
- Strategies:
  - `baseline_no_trade`
  - `perp_basis_convergence_v2`
  - `funding_crowding_fade_v2`
  - `oi_flow_breakout_v2`
  - `funding_window_timing_v1`

## Validation Plan

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py tests\historical\test_full_cycle_local_fixture_pack.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Close Evidence

Record provider collection, fixture validation, cycle evidence, fail-closed candidate-pack status, touched paths, validation results, and residual risks in `docs/stage_reports/STAGE_R56_ETHUSDT_FIXTURE_MIRROR_CYCLE_EVIDENCE_REPORT.md`, then close this work packet and ledger row if validation is clean.

Closed 2026-05-05 with validation and cycle evidence recorded in `docs/stage_reports/STAGE_R56_ETHUSDT_FIXTURE_MIRROR_CYCLE_EVIDENCE_REPORT.md`.
