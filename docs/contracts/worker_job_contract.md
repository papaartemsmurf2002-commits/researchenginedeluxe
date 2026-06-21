# V2 Worker Job Contract

Status: v2 contract foundation
Audit IDs: `V2-AUD-WORKER-001`, `V2-AUD-WORKER-005`, `V2-AUD-WORKER-006`, `V2-AUD-WORKER-007`, `V2-AUD-WORKER-008`, `V2-AUD-WORKER-009`

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
- Job outputs must include archive manifest refs, durable domain artifact refs,
  or explicit diagnostic gap records.
- `universe_refresh` jobs must run through the durable collector worker path
  with either `payload_file` or explicit `source=public_api`; public API runs
  must surface venue raw-request/raw-response provenance refs.
- `coverage_audit` jobs must run through the durable worker runner and write
  coverage/quality manifest refs instead of requiring in-process UI/API calls.
- Coverage blockers found by a successful audit are output evidence, not hidden
  logs and not worker-system failures.
- `coverage_audit` jobs may run in universe-snapshot mode with
  `archive_snapshot_id`, `universe_snapshot_id`, and `timeframe`; this mode
  must audit all in-scope universe instruments against local silver bars and
  return missing-file and coverage blocker refs without fetching venue data.
- `websocket_capture` jobs with explicit candle datatype and local source
  records may complete with raw/bronze/silver/coverage/snapshot archive refs
  plus bounded-batch caveats; other generic WebSocket capture jobs must still
  complete only with diagnostic gap evidence.
- `vectorized_backtest` jobs must run through the durable worker runner, load
  panels only through `BacktestDataService`, validate inline declarative
  strategy specs before strategy code sees rows, and return run-manifest,
  data-manifest, coverage, archive-snapshot, and universe-snapshot refs.
- Engine-level failed run manifests are research artifacts and may complete the
  worker job successfully when the worker produced the required failure
  artifacts. Data-service or strategy-spec preflight failures remain worker
  failures.
- `ledger_append_export` jobs must run through the durable worker runner, append
  one run manifest through the canonical ledger service, and optionally produce
  generated CSV/XLSX exports from the canonical Parquet ledger.
- Ledger worker jobs must reject secret-like or unsupported output path names
  before appending or exporting.
- `lead_book_upsert` jobs must run through the durable worker runner, create or
  replace one non-promotable Lead Book row through the canonical Lead Book
  service, and optionally produce a generated CSV view from the canonical
  Parquet Lead Book.
- Lead Book worker jobs must reject secret-like or unsupported output/source
  path names before writing rows or exports, and must reject job specs that try
  to override research-boundary flags.
- `audit_check` jobs must run through the durable worker runner, read durable
  job-store evidence, and write research-only JSON blocker reports.
- Audit blocker reports must treat found blockers as successful report output,
  not worker-system failure.
- Audit worker jobs must reject secret-like or unsupported report output paths
  before writing.

## Forbidden

- Long jobs inside request handlers.
- Hidden retries without job records.
- Silent stale heartbeat recovery.
- Terminal state changes without a transition record.
- Running data-quality audits against venue APIs or non-archive local files in
  the worker path.
- Running universe refresh jobs from public network sources without explicit
  `source=public_api` and unsigned public-info provenance refs.
- Running durable backtests against direct venue/API reads, unvalidated
  strategy specs, or arbitrary strategy-spec files without a trusted-file
  intake packet.
- Treating CSV/XLSX ledger exports as canonical job state.
- Writing ledger or export files to secret/local-state filenames.
- Treating generated Lead Book CSV exports as canonical job state.
- Writing Lead Book or export files to secret/local-state filenames.
- Allowing Lead Book worker job specs to set paper/live/order/sizing/runtime,
  candidate, or promotion boundary fields.
- Treating audit blocker reports as accepted-research proof or autonomous-ready
  certification.
- Writing audit blocker reports to secret/local-state filenames.
