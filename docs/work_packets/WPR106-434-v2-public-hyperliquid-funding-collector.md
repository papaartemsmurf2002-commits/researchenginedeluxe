# WPR106-434 - V2 Public Hyperliquid Funding Collector

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-COLLECT-007`
- `V2-AUD-XVENUE-004`
- `V2-AUD-ARCH-011`

## Purpose

Make the durable `funding_backfill` worker support an explicit unsigned public
Hyperliquid `/info` `fundingHistory` source mode and write returned funding
records through the existing raw, bronze, and silver archive services. This
packet closes part of the market-data archive gap required for net perpetual
returns. It does not add user funding/account endpoints, predicted funding,
WebSocket streaming, candle/trade/BBO/L2 collection, official S3 network
downloads, private Hyperliquid endpoints, account state, order placement,
sizing, runtime-mode mutation, candidate-pack behavior, or promotion behavior.

## Allowed Paths

- `docs/work_packets/WPR106-434-v2-public-hyperliquid-funding-collector.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/V2_OPERATIONS_RUNBOOK.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/venues/hyperliquid/info.py`
- `src/tradingbotsuite/v2/venues/hyperliquid/__init__.py`
- `src/tradingbotsuite/v2/archive/rebuild.py`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_universe_phase5.py`
- `tests/v2/test_workers_phase7.py`

## No-Touch Paths

No live/runtime/order placement/sizing/promotion path is in scope. This packet
must not modify user/account funding endpoints, candidate-pack truth-layer
paths, generated research evidence, legacy GUI paths, old `tradingbot`
compatibility code, secrets, credential files, lockbox policy, coverage floors,
date floors, or no-touch path policy.

## Decisions Made

- Add only the public unsigned Hyperliquid `/info` `type=fundingHistory`
  request body documented for historical funding rates.
- Treat time-range pagination as part of the funding worker contract: page
  through funding history using advancing timestamps and fail closed if the
  configured page cap is exhausted before the requested window is complete.
- Require `funding_backfill` callers to declare `source=public_api` for venue
  fetches. Existing local inline `records`, trusted `records_file`, and
  diagnostic no-record behavior remain intact.
- Preserve raw-before-parse archiving by writing venue funding rows as raw JSONL
  records before archive normalization builds bronze and silver funding tables.
- Surface page count, row count, raw payload hashes, venue adapter ID, source
  endpoint, source coin, and raw request/response IDs through durable worker
  output refs.
- Treat public funding history as intake evidence only. Coverage, backtest-data,
  and later validation gates still decide accepted research evidence; this
  packet creates no autonomous-ready, candidate-ready, paper-ready, live-ready,
  order-ready, sizing-ready, signal-ready, or promotion-ready status.

## Expected Tests

- Focused:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_universe_phase5.py tests/v2/test_workers_phase7.py -q`
- Broad v2:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
- Baseline:
  - `python -m compileall -q src/tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- Hygiene:
  - `git diff --check`

## Changed Files

- `docs/work_packets/WPR106-434-v2-public-hyperliquid-funding-collector.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/V2_OPERATIONS_RUNBOOK.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/venues/hyperliquid/info.py`
- `src/tradingbotsuite/v2/venues/hyperliquid/__init__.py`
- `src/tradingbotsuite/v2/archive/rebuild.py`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_universe_phase5.py`
- `tests/v2/test_workers_phase7.py`

## Acceptance Evidence

- Focused universe/worker lane:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_universe_phase5.py tests/v2/test_workers_phase7.py -q`
  - Result: `46 passed`
- Broad v2:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  - Result: `215 passed`
- Baseline compile:
  - `python -m compileall -q src/tradingbotsuite`
  - Result: passed
- Contract baseline:
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  - Result: `463 passed`
- Diff hygiene:
  - `git diff --check`
  - Result: passed with existing LF-to-CRLF working-copy warnings only
- Optional live public-funding smoke into a temporary archive outside the repo:
  - Durable `funding_backfill` worker with `source=public_api`,
    `instrument_id=hyperliquid:perp:BTC`, `coin=BTC`,
    `start_ts=2025-01-01T00:00:00+00:00`, and
    `end_ts=2025-01-01T04:00:00+00:00`.
  - Result: succeeded; emitted `collector_mode=public_api_funding_archive_write`,
    `source_mode=public_api`, `api_row_count=4`, `api_page_count=1`,
    `venue_adapter_id=hyperliquid_public_info_v1`,
    `source_endpoint_or_subscription=info/fundingHistory`, raw request/response
    IDs, raw payload SHA-256, and silver file IDs.

## Boundary Statement

The packet remains research-only and observe-only. Public funding collection
must not create accepted-evidence status by itself, autonomous-ready status,
candidate-pack eligibility, paper/live/order/sizing/runtime behavior, or
promotion readiness.
