# WPR106-398 V2 Durable Workers And Collector Jobs

Status: closed
Owner: Codex Research Agent
Created: 2026-06-20

## Objective

Implement Phase 7 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`: add a
durable local worker/job foundation so collection and later backtest work runs
outside ASGI/operator request handling, with SQLite WAL persistence, explicit
state transitions, heartbeat/stale evidence, worker CLI commands, initial
collector job handlers, reconnect/gap records, and an operations runbook.

This packet does not implement continuous provider collectors, full WebSocket
streaming, strategy execution, backtests, ledgers, Lead Book storage, UI,
paper/live behavior, order placement, sizing, runtime-mode changes,
candidate packs, or promotion behavior.

## Audit IDs

- `V2-AUD-WORKER-001`
- `V2-AUD-COLLECT-001`

## Dependencies

- `docs/contracts/worker_job_contract.md`
- `docs/contracts/collector_job_contract.md`
- `src/tradingbotsuite/v2/archive/**`
- `src/tradingbotsuite/v2/universe/**`
- `src/tradingbotsuite/v2/cli/main.py`

## Allowed Paths

- `docs/contracts/worker_job_contract.md`
- `docs/contracts/collector_job_contract.md`
- `docs/V2_OPERATIONS_RUNBOOK.md`
- `src/tradingbotsuite/v2/workers/**`
- `src/tradingbotsuite/v2/collectors/**`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/**`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-398-v2-durable-workers-and-collector-jobs.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Do not run long jobs inside ASGI/operator request handling.
- Do not create or modify candidate packs.
- Do not create paper/live artifacts.
- Do not place orders, change runtime mode, write live configuration, or add
  sizing/order-placement behavior.
- Collector skeletons may use local fixture payloads only; no continuous network
  collector is introduced in this packet.
- Reconnect/backoff problems must create gap records, not silent success.
- Job outputs must be tied to archive manifest refs or explicit diagnostic gap
  records.

## Acceptance Criteria

- SQLite WAL job store can initialize and persist queued jobs across process
  restart.
- Job claim, running, heartbeat, success, failure, retry, stale, and cancelled
  transitions are recorded with timestamp, worker ID, and reason.
- Worker CLI supports enqueue, run, status, retry, heartbeat, and cancel paths.
- `universe_refresh` jobs can execute from a fixture payload and produce archive
  raw/universe manifest refs.
- Recent candle bootstrap and funding backfill jobs emit API-cap warnings as
  diagnostic output refs.
- WebSocket capture skeleton records reconnect/gap records instead of silent
  success.
- Long-job execution rejects an ASGI/operator-process flag.
- Focused tests prove durability, retry/state transitions, stale heartbeats,
  CLI behavior, collector manifest ties, and reconnect gap records.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
git diff --check
```

No broad non-v2 tests are required unless shared implementation files outside
the v2 shell are changed.

## Stop Conditions

- A no-touch live/runtime/order/sizing path must be modified.
- A real continuous collector, backtest runner, strategy executor, ledger append
  workflow, Lead Book store, candidate-pack, paper/live, order, sizing, runtime,
  or promotion behavior becomes necessary.

## Completion Notes

Closed on 2026-06-20.

- Added durable worker schemas:
  - `WorkerJobRecord`
  - `WorkerHeartbeat`
  - `WorkerTransition`
  - `WorkerGapRecord`
  - `WorkerRunResult`
- Added `WorkerJobStore`, a local SQLite WAL job store with durable job rows,
  append-style transition records, heartbeat records, and gap records.
- Added explicit job statuses for queued, claimed, running, succeeded, failed,
  retrying, cancelled, and stale.
- Added state logic for claim, start, heartbeat, success, retryable failure,
  terminal failure, manual retry, cancellation, and stale heartbeat marking.
- Added `run_one_job` worker execution that claims and runs one job at a time
  and rejects ASGI/operator-process execution before claiming work.
- Added collector job schemas and initial handlers:
  - `universe_refresh` from local fixture payloads, tied to raw file and
    universe snapshot manifest refs.
  - `recent_candle_bootstrap` diagnostic skeleton with API-cap warning output.
  - `funding_backfill` diagnostic skeleton with API-cap warning output.
  - `websocket_capture` skeleton that writes reconnect/gap records instead of
    silent collection success.
- Added worker CLI commands:
  - `worker init`
  - `worker enqueue`
  - `worker run`
  - `worker status`
  - `worker retry`
  - `worker cancel`
  - `worker heartbeat`
  - `worker mark-stale`
- Added `docs/V2_OPERATIONS_RUNBOOK.md` with the Phase 7 runbook minimums.
- Updated worker and collector contracts with the concrete Phase 7 rules.
- Marked `V2-AUD-WORKER-001` and `V2-AUD-COLLECT-001` as `self_checked`.
- No continuous collectors, backtests, strategy execution, ledger append
  workflow, Lead Book storage, UI, paper/live behavior, order placement, sizing,
  runtime-mode changes, candidate-pack writing, or promotion behavior was
  implemented.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Result:

- Focused v2 tests passed: 49 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- Full `compileall` for `src\tradingbotsuite` passed.
- Contract tests passed: 462 passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
