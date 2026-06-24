# V2 Collector Job Contract

Status: v2 contract foundation
Audit IDs: `V2-AUD-WORKER-001`, `V2-AUD-COLLECT-004`, `V2-AUD-COLLECT-016`, `V2-AUD-COLLECT-019`, `V2-AUD-COLLECT-020`, `V2-AUD-COLLECT-021`, `V2-AUD-COLLECT-022`

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
- Universe refresh jobs may use `source=existing_ref` to verify an existing
  local universe snapshot row without writing universe data. Existing-ref jobs
  must require `universe_snapshot_id`, reject payload/public-source mixtures,
  fail closed on missing refs, context mismatches, non-`as_of` accepted
  evidence, or non-evidence-allowed instruments, and return
  `source_mode=existing_ref`, `universe_ref_checked=true`, and
  `universe_snapshot_id` refs.
- Durable universe refresh jobs must fail closed when none of `payload_file`,
  `source=public_api`, or `source=existing_ref` is declared.
- Recent candle bootstrap jobs with local source `records` must write raw
  candle archive files and rebuild bronze candles plus silver bars through the
  archive normalization services. They must return raw, bronze, silver,
  normalization, coverage, and optional archive snapshot refs through durable
  worker outputs.
- `websocket_capture` jobs with `datatype=candle` or `datatype=candles` and
  explicit local source `records` or trusted `records_file` may write bounded
  candle batches through the same raw candle, bronze candle, silver bar,
  coverage, and optional archive snapshot services. These jobs must return
  bounded-batch caveats and must not claim unattended continuous capture,
  historical coverage proof, accepted research evidence, or venue streaming
  operation.
- `websocket_capture` jobs with `datatype=candle` or `datatype=candles` may
  also use explicit public Hyperliquid `source=public_websocket` mode for
  bounded `candle` subscription snapshots. Public WebSocket candle jobs must
  return `source_mode`, raw payload hash, venue adapter ID, source endpoint,
  source coin, interval, raw request ID, raw response ID, WebSocket message
  count, candle row count, row/message/time caps, raw/bronze/silver refs,
  coverage refs, and optional archive snapshot refs through durable output
  refs.
- Public WebSocket candle jobs must be bounded by configured message count, row
  count, and elapsed seconds. They are recent streaming intake evidence only
  and do not prove unattended continuous capture, historical candle coverage,
  accepted research evidence, or full archive readiness.
- Public WebSocket candle, trade, BBO, and L2 jobs may opt into
  `capture_mode=unattended_session`. Session jobs must still use bounded
  message, row, and elapsed-time caps; emit `capture_mode`,
  `continuous_capture`, `accepted_historical_coverage_proof=false`, and a
  session caveat; write a durable capture-session report under the archive
  manifests tree; and preserve request/response plus archive refs.
- Public WebSocket session jobs are bounded unattended capture segments only.
  They do not prove historical coverage, full archive readiness, accepted
  research evidence, event completeness, queue/fill realism, scheduler
  operation, or promotion readiness.
- Public WebSocket candle, trade, BBO, and L2 jobs must declare
  `source_registry_source_id` matching the exact stream before stream fetch:
  `hyperliquid_ws_candle`, `hyperliquid_ws_trades`, `hyperliquid_ws_bbo`, or
  `hyperliquid_ws_l2_book`. The declared source ID must be returned through
  durable worker output refs.
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
- Recent candle bootstrap jobs may use `source=existing_ref` to verify an
  existing local silver archive snapshot without writing raw, bronze, or silver
  market data. Existing-ref archive jobs must require `archive_snapshot_id`,
  reject record/public-source mixtures, fail closed on missing snapshots,
  non-silver layers, venue/window/family/instrument/timeframe mismatches, empty
  included files, or missing manifest files, and return
  `source_mode=existing_ref`, `archive_ref_checked=true`, `archive_snapshot_id`,
  and matching `silver_file_ids` refs.
- Funding backfill jobs with local source `records` must write raw funding
  archive files and rebuild bronze funding plus silver funding intervals
  through the archive normalization services. They must return raw, bronze,
  silver, and normalization refs through durable worker outputs.
- `binance_derivatives_context_backfill` collector jobs route one Binance USD-M
  derivatives context family and symbol through bounded pagination, local raw
  and silver `derivatives_context` archive writes, and data-family coverage
  report output. They must expose source mode, family, symbol, instrument ID,
  page result ID, archive ingest ID, coverage report ID/ref, acceptance status,
  and blocker reasons through durable worker output refs.
- Binance derivatives context collector jobs may use `source=fixture_payloads`
  for deterministic offline tests or `source=public_api` for explicit
  operator-invoked public REST mode only. They are external-comparison context
  intake and do not overwrite Hyperliquid-native candle, funding, trade, BBO,
  L2, or asset-context families.
- Funding backfill jobs may also use the explicit unsigned public Hyperliquid
  `source=public_api` mode for `/info` `fundingHistory` requests. Public
  funding jobs must page through time-range responses with an advancing cursor,
  fail closed when the configured page cap is exhausted, and return page count,
  row count, raw payload hashes, venue adapter ID, source endpoint, source coin,
  and raw request/response IDs through durable output refs.
- Public funding jobs must still write raw records before archive normalization
  and must rebuild bronze funding plus silver funding intervals through the
  archive services.
- `redx collectors historical-perps` may orchestrate bounded public
  Hyperliquid current-universe candle collection across many instruments. It
  must write every collected candle slice through the existing raw, bronze, and
  silver archive services, emit a local JSON report with per-instrument
  coverage ratios, preserve `sandbox_diagnostic` evidence mode, and keep
  `accepted_research_ready=false` because the selection is current-public, not
  historical as-of universe evidence.
- `redx collectors historical-perps --candle-source trusted_records` may read
  operator-supplied Hyperliquid-native candle JSON/JSONL files for old
  intraday windows that public `candleSnapshot` cannot supply. This mode must
  require `trusted_candle_records_root`, resolve the configured per-coin file
  template inside that root, reject secret/local-state/unsafe extensions before
  archive writes, preserve records-file SHA-256 and row-count provenance, check
  symbol and timeframe when present, filter rows to the requested half-open
  window, and write only selected rows through the raw, bronze, silver, and
  coverage pipeline. It is a trusted local intake route only; it does not make
  public `candleSnapshot` a historical source and does not by itself create
  accepted research readiness.
- `redx collectors historical-perps --include-funding` may additionally write
  public Hyperliquid funding history through raw, bronze, and silver funding
  archive services for the same selected instruments. Funding collection is
  intake evidence only; accepted research still requires as-of universe,
  coverage, lockbox, validation, ledger, and audit gates.
- Candle, WebSocket candle batch, and funding archive-write jobs may read
  `records_file` inputs only when `trusted_source_root` is supplied and the
  file stays inside that root. Plain JSON arrays and JSONL/NDJSON objects are
  supported; unsafe extensions, secret-like names, path traversal, and invalid
  record shapes must fail before archive writes.
- File-backed collector jobs must return source SHA-256 and record-count refs
  through durable job output refs.
- Recent candle bootstrap jobs without local source `records` and without
  explicit `source=public_api` must keep labeling API-cap or latest-window
  limitations as diagnostic refs. Funding backfill jobs without local source
  `records` and without explicit `source=public_api` must also remain
  diagnostic. A diagnostic no-record job is not accepted research evidence.
- Generic WebSocket capture remains a skeleton unless it is an explicit
  local-record candle batch or explicit public WebSocket candle snapshot.
  Non-candle and no-record `websocket_capture` jobs must record reconnect or
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
- `websocket_trade_capture` jobs may use explicit
  `source=official_s3_node_trade_replay` mode to normalize trusted local
  JSON/JSONL files containing decompressed Hyperliquid official
  `node_fills_by_block`, `node_fills`, or `node_trades` payloads into raw
  trade microstructure rows. This mode requires `records_file` plus
  `trusted_source_root`, rejects inline `records`, performs no S3 download or
  LZ4 decompression, filters rows to the requested instrument/coin, and must
  return source hash, payload count, trade row count, skipped row count,
  dataset scope, quality/storage refs, and a coverage-certification caveat.
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
- `websocket_l2_bbo_capture` jobs may also use explicit public Hyperliquid
  `source=public_websocket` mode for bounded `bbo` or `l2Book` WebSocket
  subscription snapshots when `datatype` is `bbo` or `l2`. Public WebSocket
  BBO/L2 jobs must return `source_mode`, raw payload hash, venue adapter ID,
  source endpoint, source coin, raw request ID, raw response ID, WebSocket
  message count, stream row/level count, row/message/time caps, storage refs,
  quality refs, and explicit non-continuous caveats through durable output
  refs.
- Public WebSocket BBO/L2 jobs must be bounded by configured message count, row
  count, and elapsed seconds. They are recent streaming snapshot intake
  evidence only and do not prove unattended continuous capture, historical
  BBO/L2 coverage, accepted research evidence, queue/fill realism, or full
  archive readiness.
- `websocket_l2_bbo_capture` jobs may use explicit
  `source=official_s3_l2_replay` mode to normalize trusted local JSON/JSONL
  files containing decompressed Hyperliquid official `l2Book` payloads into BBO
  or L2 microstructure raw-capture rows. This mode requires `records_file` plus
  `trusted_source_root`, supports only `official_dataset=market_data_l2_book`,
  rejects inline `records`, performs no S3 download or LZ4 decompression, and
  must return source hash, payload count, dataset scope, quality/storage refs,
  and a non-continuous-coverage caveat.
- `official_s3_backfill` jobs may use explicit
  `source=official_s3_asset_ctxs_replay` mode to normalize trusted local
  JSON/JSONL files containing decompressed Hyperliquid official `asset_ctxs`
  payloads into raw, bronze, and silver `asset_contexts` archive layers. This
  mode requires `records_file` plus `trusted_source_root`, supports only
  `official_dataset=asset_ctxs`, rejects inline `records`, performs no S3
  download or LZ4 decompression, and must return source hash, payload count,
  context row count, dataset scope, raw/bronze/silver refs, normalization refs,
  and a non-continuous-coverage caveat.
- `official_s3_backfill` jobs may preserve local official-file fixtures in the
  raw archive and must record native file SHA-256, byte count, source endpoint,
  row count when known, and storage budget status. Hyperliquid official-file
  jobs must classify the official dataset as `market_data_l2_book`,
  `asset_ctxs`, `node_fills_by_block`, `node_fills`, or `node_trades`; reject
  unsupported official candle/OHLCV/spot-asset claims before archive writes;
  and label outputs as trusted local raw-native preservation rather than
  normalized coverage evidence.
- Trades, BBO, L2, and official-file jobs must return archive manifest refs and
  storage-growth refs through durable job output refs.
- Local fixture/source-record candle and funding jobs must not fetch from venue
  APIs. The current venue fetch exceptions are explicit `source=public_api` for
  Hyperliquid `/info` `candleSnapshot` and `/info` `fundingHistory`.
- Local fixture/source-record WebSocket candle jobs must not open venue streams.
  The current WebSocket candle exception is explicit `source=public_websocket`
  for bounded Hyperliquid `candle` subscription snapshot intake only.
- Local fixture microstructure jobs must not fetch from venue APIs. The current
  microstructure venue fetch exception is explicit `source=public_api` for
  Hyperliquid `/info` `l2Book` BBO/L2 snapshots only.
- Local fixture trade jobs must not open venue streams unless the job declares
  `source=public_websocket`; the current public WebSocket exception is
  Hyperliquid `trades` subscription snapshot intake only.
- Local fixture BBO/L2 jobs must not open venue streams unless the job declares
  `source=public_websocket`; the current public WebSocket exception is
  Hyperliquid `bbo` and `l2Book` subscription snapshot intake only.
- Public candle snapshots must not be treated as enough to satisfy six-month
  2024+ research-readiness gates because Hyperliquid documents the endpoint as
  recent-window limited.
- Public WebSocket candle snapshots must not be treated as enough to satisfy
  six-month 2024+ research-readiness gates because they are bounded recent
  stream intake, not unattended continuous capture or full historical backfill.
- Public funding history is intake evidence only; backtest-data and validation
  gates must still prove archive snapshots, coverage, 2024+ dates, six usable
  months, lockbox exclusion, and as-of universe before accepted evidence.
- Public L2/BBO snapshots are intake evidence only; backtest-data and
  validation gates must still prove archive snapshots, coverage, 2024+ dates,
  six usable months, lockbox exclusion, and as-of universe before accepted
  evidence.
- Official asset-context replay rows are intake evidence only; backtest-data
  and validation gates must still prove archive snapshots, coverage, 2024+
  dates, six usable months, lockbox exclusion, and as-of universe before
  accepted evidence.
- Public trade WebSocket snapshots are intake evidence only; backtest-data and
  validation gates must still prove archive snapshots, coverage, 2024+ dates,
  six usable months, lockbox exclusion, and as-of universe before accepted
  evidence.
- Official node fill/trade replay rows are intake evidence only; backtest-data
  and validation gates must still prove archive snapshots, coverage, 2024+
  dates, six usable months, lockbox exclusion, and as-of universe before
  accepted evidence.
- Public WebSocket candle snapshot rows are intake evidence only; backtest-data
  and validation gates must still prove archive snapshots, coverage, 2024+
  dates, six usable months, lockbox exclusion, and as-of universe before
  accepted evidence.
- Public WebSocket BBO/L2 snapshot rows are intake evidence only; backtest-data
  and validation gates must still prove archive snapshots, coverage, 2024+
  dates, six usable months, lockbox exclusion, and as-of universe before
  accepted evidence.
- Public WebSocket capture-session reports are intake evidence only;
  backtest-data and validation gates must still prove archive snapshots,
  coverage, 2024+ dates, six usable months, lockbox exclusion, and as-of
  universe before accepted evidence.
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
- Treating bounded local WebSocket candle batches as unattended continuous
  capture, full historical candle backfill, accepted historical coverage proof,
  or venue streaming operation.
- Treating bounded public WebSocket candle snapshots as unattended continuous
  capture, full historical candle backfill, or accepted historical coverage
  proof.
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
- Treating bounded public WebSocket BBO/L2 snapshots as historical BBO/L2
  coverage, unattended continuous capture, queue/fill realism, or accepted
  historical coverage proof.
- Treating bounded public WebSocket capture-session reports as accepted
  historical coverage proof, scheduler proof, queue/fill realism, full archive
  readiness, or autonomous-ready certification.
- Opening public WebSocket candle, trade, BBO, or L2 streams without the exact
  matching checked `source_registry_source_id`.
- Treating fixture microstructure captures as live execution proof or
  promotion-ready evidence.
- Treating Binance USD-M derivatives context collector outputs as
  Hyperliquid-native data, unattended broad backfill completion, accepted
  research evidence by themselves, queue/fill realism, full archive readiness,
  scheduler proof, candidate-pack evidence, paper/live/order/sizing/runtime
  evidence, or promotion-ready evidence.
