# WPR106-435 - V2 Public Hyperliquid L2/BBO Snapshot Collector

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-COLLECT-008`
- `V2-AUD-XVENUE-005`
- `V2-AUD-ARCH-012`

## Purpose

Make the durable `websocket_l2_bbo_capture` worker support an explicit unsigned
public Hyperliquid `/info` `l2Book` source mode for one-shot BBO or L2 snapshot
intake and write the derived microstructure rows through the existing raw
microstructure archive service. This closes part of the BBO/L2 intake gap
without claiming continuous WebSocket capture, queue-model realism, order-book
replay completeness, accepted evidence, paper/live readiness, order placement,
sizing, runtime mutation, candidate-pack behavior, or promotion behavior.

## Allowed Paths

- `docs/work_packets/WPR106-435-v2-public-hyperliquid-l2-bbo-snapshot-collector.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/V2_OPERATIONS_RUNBOOK.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/venues/hyperliquid/info.py`
- `src/tradingbotsuite/v2/venues/hyperliquid/__init__.py`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_universe_phase5.py`
- `tests/v2/test_microstructure_collection_phase17.py`

## No-Touch Paths

No live/runtime/order placement/sizing/promotion path is in scope. This packet
must not modify user/account endpoints, private or signed Hyperliquid
endpoints, exchange/order endpoints, candidate-pack truth-layer paths,
generated research evidence, legacy GUI paths, old `tradingbot` compatibility
code, secrets, credential files, lockbox policy, coverage floors, date floors,
or no-touch path policy.

## Decisions Made

- Add only the public unsigned Hyperliquid `/info` `type=l2Book` request body
  documented for L2 book snapshots.
- Expose `supports_bbo` and `supports_l2` on the public-info capability because
  the `l2Book` response can derive best bid/offer and summarized depth from
  public market data.
- Require `websocket_l2_bbo_capture` callers to declare `source=public_api` for
  venue snapshot fetches. Existing fixture `records` behavior remains intact.
- Convert each public `l2Book` response into exactly one archived BBO row or
  one archived L2 snapshot row, depending on the requested `datatype`.
- Preserve provenance through durable worker refs for source mode, venue
  adapter ID, endpoint, coin, raw request/response IDs, raw payload SHA-256,
  documented endpoint level cap, archive raw file ID, quality report ID, and
  storage report ID.
- Treat the new path as snapshot intake evidence only. Continuous WebSocket
  capture, historical L2 replay, and full microstructure coverage remain
  follow-up work; this packet creates no autonomous-ready, candidate-ready,
  paper-ready, live-ready, order-ready, sizing-ready, signal-ready, or
  promotion-ready status.

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

- `docs/work_packets/WPR106-435-v2-public-hyperliquid-l2-bbo-snapshot-collector.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/V2_OPERATIONS_RUNBOOK.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/venues/hyperliquid/info.py`
- `src/tradingbotsuite/v2/venues/hyperliquid/__init__.py`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_universe_phase5.py`
- `tests/v2/test_microstructure_collection_phase17.py`

## Acceptance Evidence

- Focused venue/microstructure lane:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_universe_phase5.py tests/v2/test_microstructure_collection_phase17.py -q`
  - Result: `26 passed`
- Broad v2:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  - Result: `219 passed`
- Baseline compile:
  - `python -m compileall -q src/tradingbotsuite`
  - Result: passed
- Contract baseline:
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  - Result: `463 passed`
- Diff hygiene:
  - `git diff --check`
  - Result: passed with existing LF-to-CRLF working-copy warnings only
- Optional live public-L2-book smoke into a temporary archive outside the repo:
  - Durable `websocket_l2_bbo_capture` worker with `source=public_api`,
    `datatype=bbo`, `instrument_id=hyperliquid:perp:BTC`, and `coin=BTC`.
  - Result: succeeded through the CLI worker path; emitted
    `collector_mode=public_api_l2_bbo_snapshot_capture`,
    `source_mode=public_api`, `datatype=bbo`, `api_row_count=40`,
    `venue_adapter_id=hyperliquid_public_info_v1`,
    `source_endpoint_or_subscription=info/l2Book`, raw request/response IDs,
    raw payload SHA-256, raw file ID, quality report ID, and storage report ID.
- Known limitation observed during optional smoke setup:
  - A direct fresh Python import of `WorkerJobStore` still hits the previously
    recorded P2 `ISSUE-R106-029` circular import path. The documented CLI worker
    path succeeded.

## Boundary Statement

The packet remains research-only and observe-only. Public L2/BBO snapshot
collection must not create accepted-evidence status by itself, autonomous-ready
status, candidate-pack eligibility, paper/live/order/sizing/runtime behavior,
or promotion readiness.
