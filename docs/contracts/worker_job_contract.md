# V2 Worker Job Contract

Status: v2 contract foundation
Audit ID: `V2-AUD-WORKER-001`

## Purpose

Workers run durable long-running jobs outside the ASGI/operator loop.

## Initial Schema Names

- `WorkerJobRecord`
- `WorkerHeartbeat`
- `WorkerTransition`
- `WorkerGapRecord`
- `WorkerJobStore`

## Required Rules

- Local durable job store comes first.
- SQLite WAL is the first local durable job-store backend.
- Jobs record type, input spec hash, status, attempts, heartbeat, lock owner,
  output refs, failure reason, and terminal state.
- Collectors and long backtests are not ephemeral.
- Stale heartbeats become explicit stale/failed evidence.
- State transitions are append-recorded with timestamp, worker ID, and reason.
- Supported statuses are `queued`, `claimed`, `running`, `succeeded`,
  `failed`, `retrying`, `cancelled`, and `stale`.
- Retryable failures must record `failed -> retrying -> queued`; terminal
  failures must remain terminal.
- Worker CLI commands must support initializing the store, enqueueing jobs,
  running one job, showing status, retrying, heartbeat recording, stale marking,
  and cancellation.
- Worker execution must fail before claiming work when invoked from an
  ASGI/operator-process path.
- Job outputs must include archive manifest refs or explicit diagnostic gap
  records.

## Forbidden

- Long jobs inside request handlers.
- Hidden retries without job records.
- Silent stale heartbeat recovery.
- Terminal state changes without a transition record.
