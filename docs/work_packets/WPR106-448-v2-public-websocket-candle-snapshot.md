# WPR106-448 - V2 Public WebSocket Candle Snapshot

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-COLLECT-016`
- `V2-AUD-XVENUE-012`
- `V2-AUD-ARCH-023`
- `V2-AUD-WORKER-015`

## Objective

Add explicit bounded public Hyperliquid WebSocket candle snapshot intake for
durable `websocket_capture` jobs with `datatype=candle` or `datatype=candles`.
The job must subscribe only to public market-data candle updates, stop at
declared message/row/time caps, preserve raw request/response provenance, and
write captured candle rows through the existing raw candle -> bronze candle ->
silver bar archive path.

This packet does not implement unattended continuous capture, historical candle
backfill, accepted historical coverage proof, scheduler loops, account access,
paper/live/order/sizing/runtime behavior, candidate-pack eligibility, or
promotion behavior.

## Allowed Paths

- `docs/work_packets/WPR106-448-v2-public-websocket-candle-snapshot.md`
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
- `tests/v2/test_workers_phase7.py`

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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_universe_phase5.py tests/v2/test_workers_phase7.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
git diff --check
```

## Implementation Notes

- Add `HyperliquidWebSocketClient.fetch_candle_snapshot`.
- Record `websocket/candle` source provenance, subscription payload, WebSocket
  URL, message cap, row cap, elapsed-time cap, raw payload hash, message count,
  candle row count, and bounded evidence scope.
- Route `websocket_capture` candle jobs with `source=public_websocket` through
  the public WebSocket candle intake path.
- Reject mixed `source=public_websocket` plus local `records` or
  `records_file` specs before archive writes.
- Reuse existing raw candle writer and bronze/silver rebuild services.
- Return explicit caveats:
  `continuous_capture=false`,
  `accepted_historical_coverage_proof=false`, and a bounded public-stream
  snapshot caveat.

## Decisions Made

- Added `HyperliquidWebSocketClient.fetch_candle_snapshot` for bounded public
  `candle` subscriptions.
- Marked the Hyperliquid public WebSocket capability as supporting bars while
  preserving public unsigned, research-only, no-order/no-sizing boundaries.
- Routed `websocket_capture` jobs with candle datatype and
  `source=public_websocket` through public WebSocket candle snapshot intake.
- Rejected mixed `source=public_websocket` plus local `records` or
  `records_file` before archive writes.
- Reused the existing raw candle writer, bronze candle rebuild, silver bar
  rebuild, coverage report, and optional archive snapshot path.
- Returned public WebSocket message count, candle row count, request/response
  IDs, payload hash, coin, interval, row/message/time caps, and archive refs
  through durable worker output refs.
- Kept output refs explicit that `continuous_capture=false` and
  `accepted_historical_coverage_proof=false`.
- Did not add unattended continuous capture, historical backfill, scheduler
  loops, accepted evidence, account access, paper/live/order/sizing/runtime,
  candidate-pack, or promotion behavior.

## Changed Files

- `docs/work_packets/WPR106-448-v2-public-websocket-candle-snapshot.md`
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
- `tests/v2/test_workers_phase7.py`

## Acceptance Evidence

- Focused validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_universe_phase5.py tests/v2/test_workers_phase7.py -q`
  passed with 65 tests.
- Compile validation:
  `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite` passed.
- Contract validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed with
  463 tests.
- Full v2 validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q` passed with 257 tests.
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
  capture proof, or full historical candle backfill proof.
