# WPR106-449 - V2 Public WebSocket BBO/L2 Snapshot

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-COLLECT-017`
- `V2-AUD-XVENUE-013`
- `V2-AUD-ARCH-024`
- `V2-AUD-WORKER-016`

## Objective

Add explicit bounded public Hyperliquid WebSocket BBO and L2 snapshot intake
for durable `websocket_l2_bbo_capture` jobs. The job must subscribe only to
public market-data `bbo` or `l2Book` streams, stop at declared message/row/time
caps, preserve raw request/response provenance, and write captured rows through
the existing raw microstructure capture, quality, and storage evidence path.

This packet does not implement unattended continuous capture, historical BBO/L2
coverage proof, queue/fill realism, scheduler loops, account access,
paper/live/order/sizing/runtime behavior, candidate-pack eligibility, or
promotion behavior.

## Allowed Paths

- `docs/work_packets/WPR106-449-v2-public-websocket-bbo-l2-snapshot.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/venues/hyperliquid/websocket.py`
- `src/tradingbotsuite/v2/venues/hyperliquid/__init__.py`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_universe_phase5.py`
- `tests/v2/test_microstructure_collection_phase17.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, or
  candidate-pack truth-layer paths.
- No legacy GUI paths.
- No checked historical evidence under `data/research/**`.
- No secrets, `.env`, local SQLite operator DBs, private cache, or generated
  runtime output paths.
- No lockbox, coverage-floor, date-floor, no-touch-path, credential,
  licensing, or candidate/promotion language policy changes.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_universe_phase5.py tests/v2/test_microstructure_collection_phase17.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
git diff --check
```

## Implementation Notes

- Add `HyperliquidWebSocketClient.fetch_bbo_snapshot` and
  `HyperliquidWebSocketClient.fetch_l2_book_snapshot`.
- Record `websocket/bbo` and `websocket/l2Book` source provenance,
  subscription payload, WebSocket URL, message cap, row cap, elapsed-time cap,
  raw payload hash, message count, row count, and bounded snapshot evidence
  scope.
- Route `websocket_l2_bbo_capture` jobs with `source=public_websocket` and
  `datatype=bbo` or `datatype=l2` through public WebSocket BBO/L2 snapshot
  intake.
- Reject mixed `source=public_websocket` plus local `records` or
  `records_file` specs before archive writes.
- Reuse the existing raw microstructure capture writer, quality report, and
  storage report services.
- Return explicit caveats:
  `continuous_capture=false`,
  `accepted_historical_coverage_proof=false`, and a bounded public-stream
  snapshot caveat.

## Decisions Made

- Added `HyperliquidWebSocketClient.fetch_bbo_snapshot` and
  `HyperliquidWebSocketClient.fetch_l2_book_snapshot` for bounded public
  `bbo` and `l2Book` subscriptions.
- Marked the Hyperliquid public WebSocket capability as supporting BBO and L2
  while preserving public unsigned, research-only, no-order/no-sizing
  boundaries.
- Routed `websocket_l2_bbo_capture` jobs with `datatype=bbo` or `datatype=l2`
  and `source=public_websocket` through public WebSocket snapshot intake.
- Rejected mixed `source=public_websocket` plus local `records` or
  `records_file` before archive writes.
- Parsed public WebSocket BBO payloads from the documented `bbo` tuple and
  public WebSocket L2 payloads from documented `levels` snapshots.
- Reused the existing raw microstructure capture writer, quality report, and
  storage report path.
- Returned public WebSocket message count, BBO row count or L2 level count,
  request/response IDs, payload hash, coin, row/message/time caps, quality
  refs, storage refs, archive refs, and explicit bounded snapshot caveats
  through durable worker output refs.
- Kept output refs explicit that `continuous_capture=false` and
  `accepted_historical_coverage_proof=false`.
- Did not add unattended continuous capture, historical BBO/L2 coverage proof,
  scheduler loops, accepted evidence, queue/fill realism, account access,
  paper/live/order/sizing/runtime, candidate-pack, or promotion behavior.

## Changed Files

- `docs/work_packets/WPR106-449-v2-public-websocket-bbo-l2-snapshot.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/venues/hyperliquid/websocket.py`
- `src/tradingbotsuite/v2/venues/hyperliquid/__init__.py`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_universe_phase5.py`
- `tests/v2/test_microstructure_collection_phase17.py`

## Acceptance Evidence

- Focused validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_universe_phase5.py tests/v2/test_microstructure_collection_phase17.py -q`
  passed with 49 tests.
- Compile validation:
  `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite` passed.
- Contract validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed with
  463 tests.
- Full v2 validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q` passed with 262 tests.
- Diff hygiene:
  `git diff --check` passed with line-ending warnings only.

## No-Touch Review

- No live runtime, order-placement, sizing, runtime config, promotion,
  candidate-pack truth-layer, legacy GUI, checked historical evidence, secret,
  `.env`, local SQLite operator DB, private cache, or generated runtime output
  path was changed.
- No lockbox policy, coverage floor, date floor, no-touch path, credential,
  data licensing, candidate/promotion language, or legacy evidence deletion
  decision was changed.
- No research artifact was marked autonomous-ready, candidate-ready,
  promotion-ready, paper-ready, live-ready, order-ready, sizing-ready,
  signal-ready, accepted historical coverage proof, unattended continuous
  capture proof, historical BBO/L2 coverage proof, queue/fill realism proof, or
  full archive readiness proof.
