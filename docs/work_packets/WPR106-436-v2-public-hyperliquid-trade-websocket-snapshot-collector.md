# WPR106-436 - V2 Public Hyperliquid Trade WebSocket Snapshot Collector

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-COLLECT-009`
- `V2-AUD-XVENUE-006`
- `V2-AUD-ARCH-013`

## Purpose

Make the durable `websocket_trade_capture` worker support an explicit bounded
public Hyperliquid WebSocket `trades` source mode for recent trade snapshot
intake and write the resulting trade rows through the existing raw
microstructure archive service. This closes part of the trade intake gap
without claiming full historical trade coverage, continuous production
streaming, accepted evidence, paper/live readiness, order placement, sizing,
runtime mutation, candidate-pack behavior, or promotion behavior.

## Allowed Paths

- `docs/work_packets/WPR106-436-v2-public-hyperliquid-trade-websocket-snapshot-collector.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/V2_OPERATIONS_RUNBOOK.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/archive/microstructure.py`
- `src/tradingbotsuite/v2/venues/hyperliquid/websocket.py`
- `src/tradingbotsuite/v2/venues/hyperliquid/__init__.py`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_universe_phase5.py`
- `tests/v2/test_microstructure_collection_phase17.py`

## No-Touch Paths

No live/runtime/order placement/sizing/promotion path is in scope. This packet
must not modify user/account WebSocket subscriptions, private or signed
Hyperliquid endpoints, exchange/order endpoints, candidate-pack truth-layer
paths, generated research evidence, legacy GUI paths, old `tradingbot`
compatibility code, secrets, credential files, lockbox policy, coverage floors,
date floors, or no-touch path policy.

## Decisions Made

- Add only the public Hyperliquid WebSocket subscription documented as
  `{ "type": "trades", "coin": "<coin_symbol>" }`.
- Expose a public unsigned WebSocket venue capability with `supports_trades`
  and no account/order/signing/sizing/runtime permissions.
- Require `websocket_trade_capture` callers to declare `source=public_websocket`
  for venue fetches. Existing fixture `records` behavior remains intact.
- Bound public WebSocket collection by configured message count, row count, and
  elapsed seconds so durable worker jobs are finite.
- Convert each `WsTrade` into a normalized raw microstructure trade row using
  venue time, price, size, side, and a stable trade ID based on coin/time/tid.
- Preserve provenance through durable worker refs for source mode, venue
  adapter ID, endpoint, coin, raw request/response IDs, raw payload SHA-256,
  message count, row count, storage refs, and quality refs.
- Treat the new path as recent public streaming intake only. Historical trade
  backfill and long-running continuous collection remain follow-up work; this
  packet creates no autonomous-ready, candidate-ready, paper-ready, live-ready,
  order-ready, sizing-ready, signal-ready, or promotion-ready status.

## Expected Tests

- Focused:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_universe_phase5.py tests/v2/test_microstructure_collection_phase17.py -q`
- Broad v2:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
- Baseline:
  - `python -m compileall -q src/tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- Hygiene:
  - `git diff --check`

## Changed Files

- `docs/work_packets/WPR106-436-v2-public-hyperliquid-trade-websocket-snapshot-collector.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/V2_OPERATIONS_RUNBOOK.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/archive/microstructure.py`
- `src/tradingbotsuite/v2/venues/hyperliquid/websocket.py`
- `src/tradingbotsuite/v2/venues/hyperliquid/__init__.py`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_universe_phase5.py`
- `tests/v2/test_microstructure_collection_phase17.py`

## Acceptance Evidence

- Focused venue/microstructure lane:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_universe_phase5.py tests/v2/test_microstructure_collection_phase17.py -q`
  - Result: `29 passed`
- Broad v2:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  - Result: `222 passed`
- Baseline compile:
  - `python -m compileall -q src/tradingbotsuite`
  - Result: passed
- Contract baseline:
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  - Result: `463 passed`
- Diff hygiene:
  - `git diff --check`
  - Result: passed with existing LF-to-CRLF working-copy warnings only
- Optional live public WebSocket trade smoke into a temporary archive outside
  the repo:
  - Durable `websocket_trade_capture` worker with `source=public_websocket`,
    `instrument_id=hyperliquid:perp:BTC`, `coin=BTC`, `max_public_ws_rows=1`,
    `max_public_ws_messages=5`, and `max_public_ws_seconds=20`.
  - Result: succeeded through the CLI worker path; emitted
    `collector_mode=public_websocket_trade_snapshot_capture`,
    `source_mode=public_websocket`, `datatype=trades`, archived `row_count=1`,
    `ws_message_count=2`, `ws_trade_row_count=30`,
    `venue_adapter_id=hyperliquid_public_websocket_v1`,
    `source_endpoint_or_subscription=websocket/trades`, raw request/response
    IDs, raw payload SHA-256, raw file ID, quality report ID, and storage
    report ID.

## Boundary Statement

The packet remains research-only and observe-only. Public WebSocket trade
snapshot collection must not create accepted-evidence status by itself,
autonomous-ready status, candidate-pack eligibility, paper/live/order/sizing/
runtime behavior, or promotion readiness.
