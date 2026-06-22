# V2 Worker Job Contract

Status: v2 contract foundation
Audit IDs: `V2-AUD-WORKER-001`, `V2-AUD-WORKER-005`, `V2-AUD-WORKER-006`, `V2-AUD-WORKER-007`, `V2-AUD-WORKER-008`, `V2-AUD-WORKER-009`, `V2-AUD-WORKER-013`, `V2-AUD-WORKER-014`, `V2-AUD-WORKER-015`, `V2-AUD-WORKER-018`, `V2-AUD-WORKER-019`, `V2-AUD-WORKER-020`, `V2-AUD-WORKER-021`, `V2-AUD-WORKER-022`, `V2-AUD-WORKER-023`, `V2-AUD-WORKER-024`, `V2-AUD-WORKER-025`, `V2-AUD-AUTONOMY-011`

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
- `strategy_queue_scan` jobs must run through the durable worker runner, scan
  only local JSON/YAML declarative specs through the canonical strategy-spec
  validator, write a strategy queue manifest, and return manifest path/ID/SHA,
  accepted/rejected counts, and blocker refs. If exactly one spec is accepted,
  the worker may also return normalized accepted-spec path/SHA plus
  strategy-ID/spec-hash refs. Multiple accepted specs must remain ambiguous
  blocker evidence rather than a hidden selection.
- `websocket_capture` jobs with explicit candle datatype and local source
  records may complete with raw/bronze/silver/coverage/snapshot archive refs
  plus bounded-batch caveats; other generic WebSocket capture jobs must still
  complete only with diagnostic gap evidence.
- `websocket_capture` jobs with explicit candle datatype and
  `source=public_websocket` may complete with raw/bronze/silver/coverage/
  snapshot archive refs plus public WebSocket request/response provenance,
  message/row/time caps, and bounded snapshot caveats. They must not claim
  unattended continuous capture or accepted historical coverage proof.
- `websocket_l2_bbo_capture` jobs with `datatype=bbo` or `datatype=l2` and
  `source=public_websocket` may complete with raw microstructure, quality, and
  storage refs plus public WebSocket request/response provenance,
  message/row/time caps, stream row/level counts, and bounded snapshot caveats.
  They must not claim unattended continuous capture, historical BBO/L2 coverage
  proof, queue/fill realism, or accepted historical coverage proof.
- Public WebSocket candle, trade, BBO, and L2 jobs with
  `capture_mode=unattended_session` must emit session start/archive heartbeats,
  write a capture-session report under archive manifests, return session refs,
  and keep `accepted_historical_coverage_proof=false`. These jobs are bounded
  unattended capture segments, not scheduler proof or accepted historical
  coverage proof.
- `vectorized_backtest` jobs must run through the durable worker runner, load
  panels only through `BacktestDataService`, validate declarative strategy
  specs before strategy code sees rows, and return run-manifest, data-manifest,
  coverage, archive-snapshot, and universe-snapshot refs.
- `vectorized_backtest` jobs may use either an inline `strategy_spec` object or
  a local `strategy_spec_file` with a matching `strategy_spec_file_sha256`.
  File intake must support only JSON/YAML declarative specs, reject secret-like
  or unsupported filenames, reject missing or mismatched SHA-256 values, reject
  simultaneous inline/file specs, and validate the loaded spec before any panel
  load or run artifact write.
- Engine-level failed run manifests are research artifacts and may complete the
  worker job successfully when the worker produced the required failure
  artifacts. Data-service or strategy-spec preflight failures remain worker
  failures.
- `validation_gate` jobs must run through the durable worker runner, read only
  local `run_manifest.json` and declared run artifacts, write a research-only
  validation gate manifest, and surface validation blockers as successful
  worker output rather than hidden logs.
- Validation gate worker jobs must reject secret-like or unsupported report
  output paths before writing and must not fetch venue data, rerun backtests,
  append ledgers, update Lead Book rows, or certify readiness.
- `ledger_append_export` jobs must run through the durable worker runner, append
  one run manifest through the canonical ledger service, and optionally produce
  generated CSV/XLSX exports from the canonical Parquet ledger.
- Ledger worker jobs must reject secret-like or unsupported output path names
  before appending or exporting.
- `lead_book_upsert` jobs must run through the durable worker runner, create or
  replace one non-promotable Lead Book row through the canonical Lead Book
  service, and optionally produce a generated CSV view from the canonical
  Parquet Lead Book.
- `lead_book_scan` jobs must run through the durable worker runner, filter the
  canonical Lead Book by requested lead states through the read-only scan
  service, write a JSON queue-visibility manifest, and surface missing or empty
  queues as blocker refs rather than mutating lead state.
- Lead Book worker jobs must reject secret-like or unsupported output/source
  path names before writing rows or exports, and must reject job specs that try
  to override research-boundary flags.
- `audit_check` jobs must run through the durable worker runner, read durable
  job-store evidence, and write research-only JSON blocker reports.
- Audit blocker reports must treat found blockers as successful report output,
  not worker-system failure.
- Audit worker jobs must reject secret-like or unsupported report output paths
  before writing.
- Audit worker jobs may require successful job kinds and artifact-ref prefixes
  for a selected research loop; missing required evidence must be surfaced as
  blocker refs rather than a passing report with absent evidence.
- Audit worker jobs may require successful job kinds to appear in a declared
  loop order across selected audited jobs; missing timestamps, missing ordered
  kinds, or out-of-order completion must be surfaced as blocker refs rather
  than a passing report with coincidental evidence.
- Bounded autopilot cycle planning may enqueue declared durable worker jobs and
  one generated `audit_check` job. Planning/enqueueing is not worker execution:
  queued jobs remain incomplete evidence until a worker runs them and the final
  audit report passes without blockers.
- Bounded autopilot cycle plans must require `strategy_queue_scan` after
  `coverage_audit` and before `vectorized_backtest`. The generated audit job
  must require strategy queue manifest refs, accepted spec path/SHA refs, and
  strategy spec hash refs as loop evidence.
- Bounded autopilot cycle plans must require `validation_gate` after
  `vectorized_backtest` and before ledger/Lead Book interpretation. The
  generated audit job must require validation manifest refs as loop evidence.
- Bounded autopilot cycle plans must reject unsupported worker kinds,
  user-supplied `audit_check` jobs, boundary override keys in job specs, and
  cycle sizes above the declared cap before enqueueing any jobs.
- Bounded autopilot cycle plans may declare source-output-ref to target-input
  bindings only when the source planned job precedes the target planned job.
  Binding declarations are plan metadata, not completed evidence.
- Bounded autopilot cycle execution may run enqueued planned jobs through the
  durable worker runner, but only after proving that the planned queued job is
  the next queued job for its worker kind. If a different queued job would be
  claimed first, execution must block and report the mismatch instead of
  running that kind.
- Bounded autopilot cycle execution may update a planned job input spec only
  while that job is still `queued`, only from planner-declared bindings, and
  only after the source job has succeeded with exactly one matching output ref.
  The update must recompute `input_spec_hash` and append a same-status worker
  transition before the job is claimed.
- Bounded autopilot cycle execution may skip planned jobs already in
  `succeeded` state and use their stored worker refs as audit evidence. It must
  report blockers for missing, incomplete, failed, cancelled, stale, retrying,
  or max-job-blocked planned jobs.
- Bounded autopilot scheduler ticks may select already-enqueued cycle plan
  manifests and delegate selected plans to the bounded cycle runner under
  explicit plan/job budgets. They must write scheduler session manifests and
  record deferred or rejected plans as blocker evidence. Scheduler ticks are
  not a daemon, do not bypass worker-claim rules, and do not turn queued jobs or
  passing audit reports into autonomous-ready proof.
- The executable autopilot fixture cycle may prove worker-chain operability by
  generating fixture inputs, planning/enqueueing the declared bounded cycle,
  running the real durable worker handlers through validation, and writing the
  final generated audit report. Its expected sandbox and missing-real-evidence
  blockers are successful blocker-report output, not autonomous-ready
  evidence.

## Forbidden

- Long jobs inside request handlers.
- Hidden retries without job records.
- Silent stale heartbeat recovery.
- Terminal state changes without a transition record.
- Running data-quality audits against venue APIs or non-archive local files in
  the worker path.
- Treating strategy queue worker outputs as strategy performance, validation,
  ledger, Lead Book, accepted research, or autonomous-ready evidence.
- Running universe refresh jobs from public network sources without explicit
  `source=public_api` and unsigned public-info provenance refs.
- Running public WebSocket BBO/L2 capture without explicit
  `source=public_websocket` and public WebSocket provenance refs.
- Treating public WebSocket capture-session heartbeats or reports as
  autonomous-ready certification, scheduler proof, or accepted coverage proof.
- Running durable backtests against direct venue/API reads, unvalidated
  strategy specs, arbitrary unhashed strategy-spec files, or strategy-spec
  files with missing or mismatched SHA-256 refs.
- Treating validation gate manifests as ledger rows, Lead Book updates,
  accepted research evidence, or autonomous-ready certification by themselves.
- Writing validation gate reports to secret/local-state filenames.
- Treating CSV/XLSX ledger exports as canonical job state.
- Writing ledger or export files to secret/local-state filenames.
- Treating generated Lead Book CSV exports as canonical job state.
- Writing Lead Book or export files to secret/local-state filenames.
- Allowing Lead Book worker job specs to set paper/live/order/sizing/runtime,
  candidate, or promotion boundary fields.
- Treating audit blocker reports as accepted-research proof or autonomous-ready
  certification.
- Writing audit blocker reports to secret/local-state filenames.
- Treating queued bounded-cycle jobs as completed loop evidence or treating the
  generated audit job as a substitute for running the declared workers.
- Treating a bounded cycle execution manifest as autonomous-ready proof,
  accepted historical coverage proof, candidate-pack evidence, or promotion
  evidence.
- Treating a bounded scheduler tick as a daemon, ASGI/operator in-process job
  loop, worker-claim bypass, autonomous-ready proof, accepted historical
  coverage proof, candidate-pack evidence, or promotion evidence.
- Mutating claimed, running, terminal, missing, or non-planned worker jobs
  during bounded-cycle binding.
- Treating a generated fixture worker chain as real venue archive operation,
  accepted research evidence, scheduler proof, or promotion evidence.
