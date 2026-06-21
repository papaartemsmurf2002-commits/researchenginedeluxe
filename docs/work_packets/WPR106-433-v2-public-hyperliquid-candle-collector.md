# WPR106-433 - V2 Public Hyperliquid Candle Collector

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-COLLECT-006`
- `V2-AUD-XVENUE-003`
- `V2-AUD-ARCH-010`

## Purpose

Make the durable `recent_candle_bootstrap` worker support an explicit unsigned
public Hyperliquid `/info` `candleSnapshot` source mode and write returned
market data through the existing raw, bronze, silver, coverage, and optional
snapshot archive services. This packet closes one real market-data collection
hole in the operational loop while keeping the documented Hyperliquid API
recency cap visible. It does not add funding API collection, WebSocket
streaming, official S3 network downloads, private Hyperliquid endpoints,
account state, order placement, sizing, runtime-mode mutation, candidate-pack
behavior, or promotion behavior.

## Allowed Paths

- `docs/work_packets/WPR106-433-v2-public-hyperliquid-candle-collector.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/V2_OPERATIONS_RUNBOOK.md`
- `docs/KNOWN_ISSUES.md`
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
must not modify candidate-pack truth-layer paths, generated research evidence,
legacy GUI paths, old `tradingbot` compatibility code, secrets, credential
files, lockbox policy, coverage floors, date floors, or no-touch path policy.

## Decisions Made

- Add only the public unsigned Hyperliquid `/info` `type=candleSnapshot`
  request body documented for recent candle snapshots.
- Require `recent_candle_bootstrap` callers to declare `source=public_api` for
  venue fetches. Existing local inline `records`, trusted `records_file`, and
  diagnostic no-record behavior remain intact.
- Preserve raw-before-parse archiving by writing venue candle rows as raw JSONL
  records before archive normalization builds bronze candles and silver bars.
- Surface raw request/response IDs, raw payload hash, venue adapter ID, source
  endpoint, source coin, interval, and row count through durable worker output
  refs.
- Treat public candle snapshots as intake evidence only. Coverage and later
  validation gates still decide accepted research evidence; this packet creates
  no autonomous-ready, candidate-ready, paper-ready, live-ready, order-ready,
  sizing-ready, signal-ready, or promotion-ready status.
- Record the Hyperliquid recent-window limitation: the public snapshot endpoint
  is not a full historical backfill source and cannot by itself satisfy the
  2024+ six-month autonomous-readiness data requirement.

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

- `docs/work_packets/WPR106-433-v2-public-hyperliquid-candle-collector.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/V2_OPERATIONS_RUNBOOK.md`
- `docs/KNOWN_ISSUES.md`
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
  - Result: `43 passed`
- Broad v2:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  - Result: `212 passed`
- Baseline compile:
  - `python -m compileall -q src/tradingbotsuite`
  - Result: passed
- Contract baseline:
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  - Result: `463 passed`
- Diff hygiene:
  - `git diff --check`
  - Result: passed with existing LF-to-CRLF working-copy warnings only
- Optional live public-candle smoke into a temporary archive outside the repo:
  - Durable `recent_candle_bootstrap` worker with `source=public_api`,
    `instrument_id=hyperliquid:perp:BTC`, `coin=BTC`, `timeframe=1m`,
    `start_ts=1970-01-01T00:00:00+00:00`, and
    `end_ts=2100-01-01T00:00:00+00:00`.
  - Result: succeeded; emitted `collector_mode=public_api_candle_archive_write`,
    `source_mode=public_api`, `api_row_count=5065`,
    `venue_adapter_id=hyperliquid_public_info_v1`,
    `source_endpoint_or_subscription=info/candleSnapshot`, raw request/response
    IDs, raw payload SHA-256, silver file IDs, and coverage report IDs.
- Validation follow-up issue recorded:
  - `ISSUE-R106-029` records a P2 direct worker-store import-order risk found
    during optional smoke scripting. The normal CLI worker entrypoint passed,
    so this packet did not widen into a package import refactor.

## Boundary Statement

The packet remains research-only and observe-only. Public candle collection
must not create accepted-evidence status by itself, autonomous-ready status,
candidate-pack eligibility, paper/live/order/sizing/runtime behavior, or
promotion readiness.
