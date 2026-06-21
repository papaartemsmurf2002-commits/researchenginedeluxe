# V2 Venue Adapter Contract

Status: v2 Phase 19 fixture adapter foundation
Audit ID: `V2-AUD-XVENUE-001`

## Purpose

Venue adapters expose research-safe market-data access with provenance. They
must not expose order placement, account state, signing, sizing, or runtime
execution behavior to v2 research modules.

## Initial Schema Names

- `VenueAdapterCapability`
- `VenueRawRequest`
- `VenueRawResponse`
- `HyperliquidInfoClient`
- `HyperliquidWebSocketClient`
- `BinanceFixtureArchiveResult`

## Required Rules

- Every response records venue, endpoint/source, request parameters, timestamp,
  rate-limit metadata when known, and raw payload hash.
- Provider quirks can only downgrade evidence scope.
- Venue capabilities may declare `supports_universe_metadata` for unsigned
  public metadata endpoints that feed instrument catalogs and universe
  snapshots.
- The Hyperliquid public-info adapter may call only the unsigned `/info`
  `metaAndAssetCtxs` endpoint for universe metadata, the unsigned `/info`
  `candleSnapshot` endpoint for recent candle snapshots, the unsigned `/info`
  `fundingHistory` endpoint for historical funding rates, and the unsigned
  `/info` `l2Book` endpoint for BBO/L2 snapshots. It must preserve
  `public_unsigned` access mode plus raw request/response provenance.
- Public candle snapshot provenance must record coin, interval, per-page
  start/end epoch milliseconds, raw payload hash, row count, rate-limit
  metadata when present, and the documented recent-window/5000-candle
  limitation. Multi-page collector jobs must preserve each raw request and
  response ID instead of collapsing provenance to one aggregate request.
- Public funding history provenance must record coin, start/end epoch
  milliseconds, raw payload hash, row count, rate-limit metadata when present,
  and the documented time-range pagination limitation.
- Public L2 book provenance must record coin, optional aggregation parameters,
  raw payload hash, level count, rate-limit metadata when present, and the
  documented 20-levels-per-side limitation.
- Hyperliquid official historical-file intake may preserve only trusted local
  raw copies of documented official datasets scoped by packet:
  `market_data_l2_book`, `asset_ctxs`, `node_fills_by_block`, `node_fills`, and
  `node_trades`. These records must expose source endpoint, dataset scope,
  file hash, and a raw-native/non-normalized caveat; they must not imply
  official historical candle/OHLCV coverage or normalized trade coverage.
- Hyperliquid official `market_data_l2_book` replay may normalize trusted local
  decompressed JSON/JSONL `l2Book` payload records into BBO/L2 microstructure
  rows. It must retain source-file hash and dataset scope, use an explicit
  official replay source label, and remain separate from network download,
  LZ4 decompression, continuous capture, queue/fill realism, and accepted
  coverage evidence.
- Hyperliquid official `asset_ctxs` replay may normalize trusted local
  decompressed JSON/JSONL asset-context payload records into raw, bronze, and
  silver archive context rows. It must retain source-file hash and dataset
  scope, use an explicit official replay source label, and remain separate
  from network download, LZ4 decompression, continuous context coverage, and
  accepted research evidence.
- Hyperliquid official node fill/trade replay may normalize trusted local
  decompressed JSON/JSONL `node_fills_by_block`, `node_fills`, or
  `node_trades` payload records into raw trade microstructure rows. It must
  retain source-file hash and dataset scope, filter to the requested
  instrument/coin, use an explicit official replay source label, and remain
  separate from network download, LZ4 decompression, full historical trade
  coverage proof, queue/fill realism, and accepted research evidence.
- The Hyperliquid public-WebSocket adapter may subscribe only to public market
  data streams explicitly scoped by packet. The current implemented stream is
  `trades` for bounded recent trade snapshots. It must preserve
  `public_unsigned` access mode plus raw request/response provenance.
- Public trade WebSocket provenance must record coin, subscription request,
  WebSocket URL, row/message/time caps, raw payload hash, message count, trade
  row count, and bounded snapshot evidence scope.
- Cross-venue rows preserve venue provenance and must not dilute the
  Hyperliquid-first default.
- Venue capabilities must fail closed if they declare secret access, signed
  private endpoints, account state, order placement, leverage/margin mutation,
  sizing, or runtime-mode changes.
- The first comparable non-Hyperliquid venue is a fixture-only Binance USDT-M
  adapter. It may write raw payload, silver bars, silver funding rows, coverage
  reports, universe snapshots, and archive snapshots from local fixture rows.
- Binance fixture rows must carry `venue: binance`, a namespaced
  `instrument_id`, and `venue_provenance` on every silver row.
- Binance fixture capability must not become the default primary venue;
  Hyperliquid remains the default venue until a later explicit decision.

## Forbidden

- Secret/private-key access.
- Signed trading endpoints.
- Order, account, leverage, margin, or position mutation.
- Real CCXT or venue network downloads in the Phase 19 fixture adapter path.
- Extending the Hyperliquid public-info adapter beyond unsigned universe
  metadata, recent candle snapshots, historical funding rates, and L2 book
  snapshots without a new scoped packet and boundary audit.
- Extending the Hyperliquid public-WebSocket adapter beyond bounded public
  `trades` snapshots without a new scoped packet and boundary audit.
- Treating cross-venue fixture rows as live execution proof, paper/live signal,
  sizing instruction, candidate-pack eligibility, or promotion evidence.
