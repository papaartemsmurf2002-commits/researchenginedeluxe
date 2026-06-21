# V2 Collector Job Contract

Status: v2 contract foundation
Audit IDs: `V2-AUD-WORKER-001`, `V2-AUD-COLLECT-004`

## Purpose

Collectors are durable research data jobs. They do not run inside ASGI/operator
request handling and they do not place orders.

## Initial Schema Names

- `CollectorJobRecord`
- `CollectorJobStatus`
- `MicrostructureCaptureResult`
- `MicrostructureQualityReport`
- `StorageBudgetReport`

## Required Rules

- Jobs have durable IDs, input spec hash, state, attempt count, heartbeat,
  started/finished timestamps, retry policy, output manifest refs, and failure
  reason.
- Status transitions are explicit.
- Reconnect gaps, missing periods, parse failures, and retry exhaustion are
  evidence and must be recorded.
- `universe_refresh` collector jobs may run from a local fixture payload
  (`payload_file`) or from the explicit unsigned public Hyperliquid
  `public_api` source mode. Both modes must tie outputs to raw file and
  universe snapshot manifest refs.
- Public API universe refresh jobs must return `source_mode=public_api`,
  `raw_payload_sha256`, `venue_adapter_id`, source endpoint, raw request ID,
  and raw response ID through durable output refs.
- Durable universe refresh jobs must fail closed when neither `payload_file`
  nor `source=public_api` is declared.
- Recent candle bootstrap jobs with local source `records` must write raw
  candle archive files and rebuild bronze candles plus silver bars through the
  archive normalization services. They must return raw, bronze, silver,
  normalization, coverage, and optional archive snapshot refs through durable
  worker outputs.
- Funding backfill jobs with local source `records` must write raw funding
  archive files and rebuild bronze funding plus silver funding intervals
  through the archive normalization services. They must return raw, bronze,
  silver, and normalization refs through durable worker outputs.
- Candle and funding archive-write jobs may read `records_file` inputs only
  when `trusted_source_root` is supplied and the file stays inside that root.
  Plain JSON arrays and JSONL/NDJSON objects are supported; unsafe extensions,
  secret-like names, path traversal, and invalid record shapes must fail before
  archive writes.
- File-backed collector jobs must return source SHA-256 and record-count refs
  through durable job output refs.
- Recent candle bootstrap and funding backfill jobs without local source
  `records` must keep labeling API-cap or latest-window limitations as
  diagnostic refs. A diagnostic no-record job is not accepted research
  evidence.
- WebSocket capture in Phase 7 is a skeleton only. It must record reconnect or
  gap evidence instead of reporting silent collection success.
- `websocket_trade_capture` jobs may preserve fixture trade records to the raw
  archive, but they must not open venue network streams in this phase.
- `websocket_l2_bbo_capture` jobs may preserve fixture BBO or L2 records to the
  raw archive, but they must not claim queue-model or fill realism.
- `official_s3_backfill` jobs may preserve local official-file fixtures in the
  raw archive and must record native file SHA-256, byte count, source endpoint,
  row count when known, and storage budget status.
- Trades, BBO, L2, and official-file jobs must return archive manifest refs and
  storage-growth refs through durable job output refs.
- Candle and funding archive-write jobs must not fetch from venue APIs in the
  current fixture/source-record collector path.
- Candle and funding archive-write jobs must not read arbitrary local files
  outside a trusted source root.
- Reconnect attempts, gap reasons, missing periods, and retry evidence must be
  linked to worker gap records instead of hidden in logs.
- Storage budget and retention/backup policy records are evidence only; they do
  not authorize deletion, movement, upload, or overwrite behavior.
- Collector jobs preserve `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Forbidden

- Ephemeral long-running collector state.
- Silent gap filling.
- Live/paper/order/sizing/runtime mutation.
- Claiming accepted evidence from diagnostic collector skeleton outputs.
- Claiming accepted evidence from fixture/source-record collector outputs
  unless later backtest-data and validation gates explicitly accept a separate
  archive snapshot.
- Silent public network universe refreshes when the job spec does not declare
  `source=public_api`.
- Reading `.env`, credential/key-like, pickle-like, SQLite/database, compressed,
  executable, or archive files as collector record sources.
- Real venue WebSocket streaming or S3 network downloads in the Phase 17 fixture
  collector path.
- Treating fixture microstructure captures as live execution proof or
  promotion-ready evidence.
