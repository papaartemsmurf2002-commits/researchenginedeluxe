# WPR106-445 - V2 WebSocket Candle Batch Archive

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-COLLECT-015`
- `V2-AUD-WORKER-012`
- `V2-AUD-ARCH-022`

## Objective

Add a bounded archive-write path for durable `websocket_capture` jobs when the
job explicitly declares candle data and supplies local source records. This
lets manager/orchestrator runs preserve a captured candle batch through the
existing raw -> bronze -> silver bars -> coverage/snapshot archive services
while retaining diagnostic gap evidence for generic, non-candle, or no-record
WebSocket capture jobs.

This packet does not add unattended venue WebSocket streaming, public network
capture, historical candle backfill, accepted research evidence, continuous
coverage proof, candidate/promotion behavior, or paper/live/order/sizing/
runtime behavior.

## Allowed Paths

- `docs/work_packets/WPR106-445-v2-websocket-candle-batch-archive.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/collectors/jobs.py`
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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
git diff --check
```

## Implementation Notes

- Route only `websocket_capture` jobs with `datatype` of `candle`/`candles`
  and an explicit local source (`records` or trusted `records_file`) into the
  archive-write path.
- Reuse the existing candle archive normalization services and trusted
  records-file guards.
- Preserve the existing WebSocket gap-record skeleton for non-candle and
  no-record `websocket_capture` jobs.
- Return durable output refs for collector mode, source refs, raw/bronze/
  silver/normalization/coverage/snapshot refs, and an explicit bounded-batch
  caveat.
- Label this mode as bounded batch capture, not unattended continuous capture
  and not accepted historical coverage proof.

## Decisions Made

- Added a candle-datatype branch to durable `websocket_capture` jobs that
  runs only when `records` or trusted `records_file` is present.
- Reused the existing raw candle writer plus bronze candle, silver bar,
  coverage, and optional archive snapshot rebuild services.
- Preserved generic WebSocket capture as a gap-record skeleton for non-candle
  datatypes and no-record jobs.
- Returned durable output refs for source mode, source endpoint/subscription,
  row count, source SHA/record count refs, archive refs, and bounded-batch
  caveats.
- Recorded optional gap evidence for candle batch jobs when `gap_reason` or
  `reconnect_attempts` is present.
- Kept this path local-record only; no venue WebSocket client, public network
  intake, full historical backfill, accepted evidence, or continuous coverage
  proof was added.

## Changed Files

- `docs/work_packets/WPR106-445-v2-websocket-candle-batch-archive.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_workers_phase7.py`

## Acceptance Evidence

- Focused validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py -q`
  passed with 42 tests.
- Compile validation:
  `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite` passed.
- Contract validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed with
  463 tests.
- Full v2 validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q` passed with 249 tests.
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
  signal-ready, accepted historical coverage proof, or unattended continuous
  capture proof.
