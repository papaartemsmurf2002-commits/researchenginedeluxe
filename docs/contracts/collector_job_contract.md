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
- Recent candle bootstrap jobs may also use the explicit unsigned public
  Hyperliquid `source=public_api` mode for `/info` `candleSnapshot` requests.
  Public candle jobs must split requested time ranges into fixed-width page
  windows no larger than configured `max_candles_per_public_page` and must fail
  closed if the configured page size exceeds the documented 5000-candle cap or
  when `max_public_info_pages` is exhausted. They must return
  `source_mode=public_api`, page count, row count, raw payload hashes, venue
  adapter ID, source endpoint, raw request IDs, raw response IDs, source coin,
  interval, and the documented recent-window cap through durable output refs.
- Public candle snapshot jobs must still write raw records before archive
  normalization and must rebuild bronze candles plus silver bars through the
  archive services. The public snapshot endpoint is a recent-window source, not
  full historical backfill evidence.
- Funding backfill jobs with local source `records` must write raw funding
  archive files and rebuild bronze funding plus silver funding intervals
  through the archive normalization services. They must return raw, bronze,
  silver, and normalization refs through durable worker outputs.
- Funding backfill jobs may also use the explicit unsigned public Hyperliquid
  `source=public_api` mode for `/info` `fundingHistory` requests. Public
  funding jobs must page through time-range responses with an advancing cursor,
  fail closed when the configured page cap is exhausted, and return page count,
  row count, raw payload hashes, venue adapter ID, source endpoint, source coin,
  and raw request/response IDs through durable output refs.
- Public funding jobs must still write raw records before archive normalization
  and must rebuild bronze funding plus silver funding intervals through the
  archive services.
- Candle and funding archive-write jobs may read `records_file` inputs only
  when `trusted_source_root` is supplied and the file stays inside that root.
  Plain JSON arrays and JSONL/NDJSON objects are supported; unsafe extensions,
  secret-like names, path traversal, and invalid record shapes must fail before
  archive writes.
- File-backed collector jobs must return source SHA-256 and record-count refs
  through durable job output refs.
- Recent candle bootstrap jobs without local source `records` and without
  explicit `source=public_api` must keep labeling API-cap or latest-window
  limitations as diagnostic refs. Funding backfill jobs without local source
  `records` and without explicit `source=public_api` must also remain
  diagnostic. A diagnostic no-record job is not accepted research evidence.
- WebSocket capture in Phase 7 is a skeleton only. It must record reconnect or
  gap evidence instead of reporting silent collection success.
- `websocket_trade_capture` jobs may preserve fixture trade records to the raw
  archive.
- `websocket_trade_capture` jobs may also use explicit public Hyperliquid
  `source=public_websocket` mode for bounded `trades` WebSocket subscription
  snapshots. Public trade WebSocket jobs must return `source_mode`,
  raw payload hash, venue adapter ID, source endpoint, source coin, raw
  request ID, raw response ID, WebSocket message count, trade row count,
  row/message/time caps, storage refs, and quality refs through durable output
  refs.
- Public trade WebSocket jobs must be bounded by configured message count, row
  count, and elapsed seconds. They are recent streaming intake evidence only
  and do not prove historical trade coverage, long-running continuous capture,
  accepted research evidence, or queue/fill realism.
- `websocket_l2_bbo_capture` jobs may preserve fixture BBO or L2 records to the
  raw archive, but they must not claim queue-model or fill realism.
- `websocket_l2_bbo_capture` jobs may also use explicit unsigned public
  Hyperliquid `source=public_api` mode for `/info` `l2Book` one-shot snapshots
  when `datatype` is `bbo` or `l2`. Public snapshot jobs must return
  `source_mode=public_api`, raw payload hash, venue adapter ID, source endpoint,
  source coin, row count, raw request ID, raw response ID, storage refs, quality
  refs, and the documented 20-levels-per-side cap through durable output refs.
- Public `l2Book` jobs must write one normalized microstructure raw-capture row
  per venue response. They are snapshot intake evidence only and do not prove
  continuous WebSocket capture, historical L2 replay, queue-model realism, or
  accepted research evidence.
- `official_s3_backfill` jobs may preserve local official-file fixtures in the
  raw archive and must record native file SHA-256, byte count, source endpoint,
  row count when known, and storage budget status.
- Trades, BBO, L2, and official-file jobs must return archive manifest refs and
  storage-growth refs through durable job output refs.
- Local fixture/source-record candle and funding jobs must not fetch from venue
  APIs. The current venue fetch exceptions are explicit `source=public_api` for
  Hyperliquid `/info` `candleSnapshot` and `/info` `fundingHistory`.
- Local fixture microstructure jobs must not fetch from venue APIs. The current
  microstructure venue fetch exception is explicit `source=public_api` for
  Hyperliquid `/info` `l2Book` BBO/L2 snapshots only.
- Local fixture trade jobs must not open venue streams unless the job declares
  `source=public_websocket`; the current public WebSocket exception is
  Hyperliquid `trades` subscription snapshot intake only.
- Public candle snapshots must not be treated as enough to satisfy six-month
  2024+ research-readiness gates because Hyperliquid documents the endpoint as
  recent-window limited.
- Public funding history is intake evidence only; backtest-data and validation
  gates must still prove archive snapshots, coverage, 2024+ dates, six usable
  months, lockbox exclusion, and as-of universe before accepted evidence.
- Public L2/BBO snapshots are intake evidence only; backtest-data and
  validation gates must still prove archive snapshots, coverage, 2024+ dates,
  six usable months, lockbox exclusion, and as-of universe before accepted
  evidence.
- Public trade WebSocket snapshots are intake evidence only; backtest-data and
  validation gates must still prove archive snapshots, coverage, 2024+ dates,
  six usable months, lockbox exclusion, and as-of universe before accepted
  evidence.
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
- Unbounded venue WebSocket streaming or S3 network downloads in the Phase 17
  fixture collector path.
- Treating bounded public trade WebSocket snapshots as historical trade
  coverage or as continuous production stream operation.
- Treating one-shot public `l2Book` snapshots as continuous BBO/L2 archive
  coverage or as historical microstructure replay.
- Treating fixture microstructure captures as live execution proof or
  promotion-ready evidence.
