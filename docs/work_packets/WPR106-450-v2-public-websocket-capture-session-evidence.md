# WPR106-450 - V2 Public WebSocket Capture Session Evidence

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-COLLECT-018`
- `V2-AUD-XVENUE-014`
- `V2-AUD-ARCH-025`
- `V2-AUD-WORKER-017`

## Objective

Add explicit bounded unattended public WebSocket capture-session evidence for
durable Hyperliquid candle, trade, BBO, and L2 WebSocket collector jobs. A
session run must declare `capture_mode=unattended_session`, collect only public
market-data streams already scoped by earlier packets, preserve raw
request/response provenance, emit worker heartbeats, write a durable session
report under the archive manifests tree, and keep all outputs
research-only/non-promotable.

This packet does not implement a scheduler daemon, infinite stream process,
historical coverage proof, accepted research evidence, queue/fill realism,
paper/live/order/sizing/runtime behavior, candidate-pack eligibility, or
promotion behavior.

## Allowed Paths

- `docs/work_packets/WPR106-450-v2-public-websocket-capture-session-evidence.md`
- `docs/contracts/archive_contract.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/venues/hyperliquid/websocket.py`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_universe_phase5.py`
- `tests/v2/test_workers_phase7.py`
- `tests/v2/test_microstructure_collection_phase17.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, or
  candidate-pack truth-layer paths.
- No legacy GUI paths.
- No checked historical evidence under `data/research/**`.
- No secrets, `.env`, local SQLite operator DBs, private cache, or generated
  runtime output paths outside test temp directories.
- No lockbox, coverage-floor, date-floor, no-touch-path, credential,
  licensing, or candidate/promotion language policy changes.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_universe_phase5.py tests/v2/test_workers_phase7.py tests/v2/test_microstructure_collection_phase17.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
git diff --check
```

## Implementation Notes

- Keep default public WebSocket jobs as bounded snapshots.
- Add opt-in `capture_mode=unattended_session` handling for public WebSocket
  candle, trade, BBO, and L2 jobs.
- Write a deterministic JSON session report under
  `manifests/websocket_capture_sessions/` with stream, caps, provenance IDs,
  row counts, archive refs, boundary flags, and explicit caveats.
- Emit worker heartbeats at session start and after archive/session report
  persistence.
- Keep `accepted_historical_coverage_proof=false` for session output.
- Make the public WebSocket adapter stop cleanly on receive timeout after at
  least one message, while still failing closed when no message arrives.

## Decisions Made

- Kept default public WebSocket collector behavior as bounded snapshots.
- Added opt-in `capture_mode=unattended_session` for public WebSocket candle,
  trade, BBO, and L2 collector jobs.
- Wrote capture-session JSON reports under
  `manifests/websocket_capture_sessions/` with stream, datatype, instrument,
  coin, timestamps, caps, raw request/response refs, payload hash, row counts,
  archive refs, and the full research-only boundary invariant.
- Emitted worker heartbeats at session start and after archive/session-report
  persistence.
- Returned session refs, `unattended_capture_session=true`,
  `continuous_capture_segment=true`, `continuous_capture=true`, and
  `accepted_historical_coverage_proof=false` through durable worker outputs.
- Preserved partial public WebSocket captures when a receive timeout occurs
  after at least one message, while still failing closed when no messages
  arrive.
- Did not add scheduler daemon behavior, infinite streaming, accepted
  historical coverage proof, queue/fill realism, account access,
  paper/live/order/sizing/runtime, candidate-pack, or promotion behavior.

## Changed Files

- `docs/work_packets/WPR106-450-v2-public-websocket-capture-session-evidence.md`
- `docs/contracts/archive_contract.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/venues/hyperliquid/websocket.py`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_universe_phase5.py`
- `tests/v2/test_workers_phase7.py`
- `tests/v2/test_microstructure_collection_phase17.py`

## Acceptance Evidence

- Focused validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_universe_phase5.py tests/v2/test_workers_phase7.py tests/v2/test_microstructure_collection_phase17.py -q`
  passed with 104 tests.
- Compile validation:
  `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite` passed.
- Contract validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed with
  463 tests.
- Full v2 validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q` passed with 268 tests.
- Diff hygiene:
  `git diff --check` passed with line-ending warnings only.

## No-Touch Review

- No live runtime, order-placement, sizing, runtime config, promotion,
  candidate-pack truth-layer, legacy GUI, checked historical evidence, secret,
  `.env`, local SQLite operator DB, private cache, or generated runtime output
  path outside test temp directories was changed.
- No lockbox policy, coverage floor, date floor, no-touch path, credential,
  data licensing, candidate/promotion language, or legacy evidence deletion
  decision was changed.
- No research artifact was marked autonomous-ready, candidate-ready,
  promotion-ready, paper-ready, live-ready, order-ready, sizing-ready,
  signal-ready, accepted historical coverage proof, scheduler proof, queue/fill
  realism proof, or full archive readiness proof.
