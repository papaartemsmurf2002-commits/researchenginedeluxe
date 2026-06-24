# V2 Hyperliquid Data Venue Roadmap

Status: roadmap draft, research-only
Date: 2026-06-22
Scope: free/public data venues for historical and forward-captured research data covering liquid Hyperliquid perpetual assets

This document turns the data-venue research into an implementation roadmap for the v2 Hyperliquid-first research archive. It is a planning document only. It does not add trading behavior, paper/live behavior, order placement, sizing, promotion, or runtime-mode changes.

## 0. Boundary and operating mode

The v2 product scope is a research-only, data-first, multi-instrument perpetual-futures platform focused on Hyperliquid perpetuals above USD 5,000,000 daily notional volume, with compatible multi-venue comparison data, strict validation, owned archives, and audit-backed research loops.

This roadmap keeps the repository in observe-only research mode:

```json
{
  "research_only": true,
  "observe_only": true,
  "promotion_ready": false,
  "candidate_evidence": false,
  "candidate_pack_eligible": false,
  "live_signal": false,
  "paper_signal": false,
  "sizing_instruction": false,
  "order_placement_instruction": false,
  "runtime_mode_change": false
}
```

Implementation packets derived from this roadmap must avoid no-touch paths unless the packet explicitly scopes the path, risk, rollback, and validation. Generated data must stay under ignored local archive paths and must be manifest-backed.

## 1. Goal

Build a reproducible, free/public-source historical data archive for liquid Hyperliquid perpetual assets. The archive must support:

1. as-of Hyperliquid universe snapshots;
2. raw venue provenance for every downloaded or captured payload;
3. candles, trades, funding, open interest, asset contexts, BBO, and L2 order book data;
4. reconstruction of 1m/5m/higher bars from raw trades or fills where possible;
5. cross-venue comparison features without pretending external venues are Hyperliquid-native fills;
6. data-family coverage audits rather than a single candle-only coverage metric;
7. evidence gates matching the v2 floor: 2024-01-01+ start, at least 6 usable months, 12 months preferred, 0.98 coverage, as-of universe snapshots, lockbox exclusion, and manifest-backed costs/funding/spread/slippage/impact/liquidity assumptions.

## 2. Strict-free policy

The project should distinguish free/public access types. Do not collapse them into one field.

| Cost class | Meaning | Default behavior |
| --- | --- | --- |
| `zero_cost_public` | No paid tier, no account, no secret, no transfer charge expected for normal use. | Allowed by default. |
| `public_rate_limited` | Free public endpoint with documented or observed rate limits. | Allowed by default with backoff and page caps. |
| `free_sample_only` | Free sample data only; useful for schema tests but not full coverage. | Diagnostic only. |
| `public_requester_pays_transfer` | Public data, but requester pays network/storage transfer. | Disabled under strict-zero-dollar mode unless an explicit operator packet allows it. |
| `paid_or_keyed` | Paid vendor, paid tier, private credentials, or account-specific export. | Out of scope for this roadmap. |

Important consequence: Hyperliquid official historical files are native and valuable, but the published access path is requester-pays. Under strict-zero-dollar mode, those jobs stay quarantined. Under an explicit operator-approved public-requester-pays mode, they can be ingested with `accepted_under_strict_free=false` and used for native-orderflow research only after separate coverage audits.

## 3. Target data families

Candles are not enough. The archive should store raw and normalized layers for these families:

| Family | Primary Hyperliquid source | External complements | Research use |
| --- | --- | --- | --- |
| Universe metadata | Hyperliquid `meta`, `metaAndAssetCtxs`, `allPerpMetas` | Exchange info from Binance, Bybit, OKX, Bitget, MEXC, Gate, KuCoin, HTX, dYdX | as-of liquid universe, symbol mapping, delisting/remap tracking |
| Asset contexts | Hyperliquid `metaAndAssetCtxs` and official `asset_ctxs` files if enabled | Mark/index/OI/funding endpoints from external venues | day notional, mark, oracle, funding, open interest, impact-price context |
| Funding | Hyperliquid `fundingHistory`, `predictedFundings` | Binance, Bybit, OKX, Bitget, MEXC, Gate, KuCoin, HTX, dYdX, Deribit | net-return modeling, carry regimes, basis and crowding features |
| Candles | Hyperliquid recent `candleSnapshot`; derived from Hyperliquid trades/fills; forward WS candles | Binance Vision klines, Bybit/OKX/Bitget/MEXC/Gate/KuCoin/HTX klines | bar panels, sanity checks, fallback external comparison |
| Trades/fills | Hyperliquid WS `trades`; official `node_fills_by_block`, `node_fills`, `node_trades` if enabled | Binance Vision trades/aggTrades, Bybit historical trades, OKX history trades, MEXC deals, Gate/KuCoin/HTX trades, dYdX trades | bar reconstruction, taker imbalance, VWAP, volume shocks, microstructure features |
| BBO | Hyperliquid WS `bbo`; recent `l2Book` top level | External book-ticker/BBO/orderbook endpoints | spread, liquidity stress, quote pressure |
| L2 order book | Hyperliquid recent `l2Book`; WS `l2Book`; official `market_data/l2Book` if enabled | OKX/Bybit/Binance/Bitget/MEXC/Gate/KuCoin/HTX depth endpoints/streams | depth imbalance, book slope, impact/slippage models |
| Open interest | Hyperliquid asset contexts | Binance OI, OKX OI, Bybit OI, Bitget OI, MEXC hold volume, KuCoin/HTX OI | capacity and crowding filters |
| Liquidations / stress flow | Hyperliquid fills and liquidation-related native records where available | Binance/HTX/other liquidation records or streams, Crypto Lake sample diagnostics | stress labels and forced-flow regimes |
| Spot/oracle context | Hyperliquid oracle context | Coinbase, Kraken, Pyth, DefiLlama, DexScreener, GeckoTerminal | fair-value, on-chain liquidity, oracle dislocation context |

## 4. Source priority list

### P0 native and backbone sources

| Source ID | Cost class | Families | Action |
| --- | --- | --- | --- |
| `hyperliquid_info_meta_asset_ctxs` | `zero_cost_public` | universe, asset contexts, day notional, mark, funding, OI | Implement first. Required for as-of universe selection. |
| `hyperliquid_info_funding_history` | `zero_cost_public` | funding | Implement first. Page by time and store raw request/response provenance. |
| `hyperliquid_info_candle_snapshot_recent` | `zero_cost_public` | recent candles | Implement as recent-window sanity check, not full historical proof. |
| `hyperliquid_info_l2_book_snapshot` | `zero_cost_public` | recent L2 snapshot | Implement as snapshot intake with 20-level cap caveat. |
| `hyperliquid_ws_trades` | `zero_cost_public` | forward trades | Implement bounded capture sessions with heartbeat/gap reports. |
| `hyperliquid_ws_bbo` | `zero_cost_public` | forward BBO | Implement bounded capture sessions. |
| `hyperliquid_ws_l2_book` | `zero_cost_public` | forward L2 | Implement bounded capture sessions. |
| `binance_vision_usdm_trades` | `zero_cost_public` | futures trades | Implement as external historical orderflow backbone. |
| `binance_vision_usdm_agg_trades` | `zero_cost_public` | futures aggTrades | Implement as compressed fallback to trades where needed. |
| `binance_vision_usdm_klines` | `zero_cost_public` | futures candles | Implement as external bar backbone and integrity cross-check. |
| `binance_usdm_public_derivatives_context` | `public_rate_limited` | funding, OI, taker buy/sell, mark/index/premium klines | Implement after Binance Vision history. |

### P1 complementary derivative venues

| Source ID | Cost class | Families | Action |
| --- | --- | --- | --- |
| `bybit_public_market` | `public_rate_limited` | klines, recent trades, orderbook, funding, OI | Add after Binance. Prefer official historical download for older trades when free/public. |
| `okx_public_market` | `public_rate_limited` | candles, trades, books, funding, OI | Add for high-quality swap comparison. Track endpoint lookback limits explicitly. |
| `dydx_indexer_public` | `public_rate_limited` | markets, candles, trades, orderbook, funding | Add for CLOB-perp comparison where universe overlaps. |
| `deribit_public` | `public_rate_limited` | BTC/ETH/SOL-like derivatives, trades, orderbook, funding | Add for major-asset derivative context. |

### P2 alt coverage fillers

| Source ID | Cost class | Families | Action |
| --- | --- | --- | --- |
| `bitget_public_mix_market` | `public_rate_limited` | futures candles, funding, OI, depth, recent/historical trades | Add for alt-perp gaps; store lookback constraints per endpoint. |
| `mexc_contract_public` | `public_rate_limited` | contract metadata, depth, depth commits, klines, deals, funding | Add for smaller Hyperliquid alts. Validate quality before use in features. |
| `gate_futures_public` | `public_rate_limited` | candles, trades, orderbook, funding | Add as gap filler. Verify per-symbol availability. |
| `kucoin_futures_public` | `public_rate_limited` | klines, trades, orderbook, funding, OI | Add as gap filler. Offline public download path needs separate verification. |
| `htx_swap_public` | `public_rate_limited` | depth, BBO, klines, trades, OI, funding, liquidations | Add for additional perp and liquidation context. |

### P3 reference/context sources

| Source ID | Cost class | Families | Action |
| --- | --- | --- | --- |
| `coinbase_spot_public` | `public_rate_limited` | spot candles, trades, book | Use as USD spot reference for overlapping majors/alts. |
| `kraken_spot_public` | `public_rate_limited` | spot OHLC, trades, book | Use as secondary spot reference. |
| `pyth_hermes_public` | `public_rate_limited` | oracle prices | Use for oracle/fair-value sanity checks. |
| `defillama_public` | `zero_cost_public` | prices, DEX volume, open interest context, fees/revenue context | Use as macro/on-chain context only. |
| `dexscreener_public` | `public_rate_limited` | DEX pair liquidity/volume/txns | Use for token liquidity context. |
| `geckoterminal_public` | `public_rate_limited` | DEX/on-chain token market data | Use for token liquidity context. |
| `crypto_lake_free_sample` | `free_sample_only` | sample candles/trades/funding/OI/liquidations | Use only for schema smoke tests and fallback diagnostics. |

### Quarantined native official files

| Source ID | Cost class | Families | Action |
| --- | --- | --- | --- |
| `hyperliquid_official_s3_l2_book` | `public_requester_pays_transfer` | native historical L2 snapshots | Keep disabled in strict-zero-dollar mode. Optional explicit packet only. |
| `hyperliquid_official_s3_asset_ctxs` | `public_requester_pays_transfer` | native asset contexts | Keep disabled in strict-zero-dollar mode. Optional explicit packet only. |
| `hyperliquid_official_s3_node_fills_by_block` | `public_requester_pays_transfer` | native fills/trade reconstruction | Keep disabled in strict-zero-dollar mode. Optional explicit packet only. |
| `hyperliquid_official_s3_node_fills` | `public_requester_pays_transfer` | older native fills | Keep disabled in strict-zero-dollar mode. Optional explicit packet only. |
| `hyperliquid_official_s3_node_trades` | `public_requester_pays_transfer` | older native trade records | Keep disabled in strict-zero-dollar mode. Optional explicit packet only. |

## 5. Archive layout

Recommended local ignored path:

```text
data/research/v2_market_archive/
  manifests/
    source_registry/
    symbol_maps/
    archive_snapshots/
    coverage_reports/
    quality_reports/
    capture_sessions/
  raw/
    venue=<venue>/source=<source_id>/family=<family>/symbol=<symbol>/date=<yyyy-mm-dd>/...
  bronze/
    venue=<venue>/family=<family>/symbol=<symbol>/date=<yyyy-mm-dd>/...
  silver/
    bars_1m/venue=<venue>/symbol=<symbol>/date=<yyyy-mm-dd>/...
    trades/venue=<venue>/symbol=<symbol>/date=<yyyy-mm-dd>/...
    funding/venue=<venue>/symbol=<symbol>/...
    asset_contexts/venue=<venue>/symbol=<symbol>/...
    bbo/venue=<venue>/symbol=<symbol>/date=<yyyy-mm-dd>/...
    l2_snapshots/venue=<venue>/symbol=<symbol>/date=<yyyy-mm-dd>/...
  gold/
    feature_panels/as_of_universe=<snapshot_id>/interval=1m/...
    cross_venue_panels/as_of_universe=<snapshot_id>/interval=1m/...
```

Layer rules:

- `raw`: original downloaded/captured payloads, request metadata, response metadata, checksums, and source hashes. Never mutate.
- `bronze`: parsed records with source fields preserved, but minimal interpretation.
- `silver`: normalized schemas by family and venue; timestamps, symbols, units, and sides standardized.
- `gold`: derived feature panels and joined research data. Every gold panel must reference archive snapshot, universe snapshot, source registry version, symbol map version, and coverage report.

## 6. Core schemas

### 6.1 Source registry entry

```yaml
source_id: binance_vision_usdm_trades
venue: binance
market_type: perpetual
native_to_hyperliquid: false
cost_class: zero_cost_public
auth_required: false
secret_required: false
paid_required: false
data_families:
  - trades
history_mode: public_daily_monthly_archive
priority: P0
research_role: external_historical_orderflow_backbone
rate_limit_policy:
  max_parallel_downloads: 4
  retry_backoff_seconds: [1, 2, 5, 10]
provenance_required:
  - source_url
  - downloaded_at_utc
  - source_file_sha256
  - checksum_sha256_when_available
  - row_count
  - byte_count
caveats:
  - external venue; never relabel as Hyperliquid-native fills
```

### 6.2 Hyperliquid source registry entry

```yaml
source_id: hyperliquid_info_candle_snapshot_recent
venue: hyperliquid
market_type: perpetual
native_to_hyperliquid: true
cost_class: zero_cost_public
auth_required: false
data_families:
  - candles
history_mode: recent_window_api
priority: P0
research_role: recent_native_sanity_check
accepted_historical_coverage_proof: false
caveats:
  - recent-window limited
  - not enough by itself for 6-month or 12-month evidence windows
```

### 6.3 Quarantined official-file registry entry

```yaml
source_id: hyperliquid_official_s3_node_fills_by_block
venue: hyperliquid
market_type: perpetual
native_to_hyperliquid: true
cost_class: public_requester_pays_transfer
strict_zero_dollar_allowed: false
auth_required: false
data_families:
  - fills
  - derived_trades
history_mode: official_public_archive_requester_pays
priority: P0_quarantined
research_role: native_historical_trade_reconstruction_if_operator_approved
accepted_under_strict_free: false
required_operator_gate:
  - explicit_packet_scope
  - transfer_cost_acknowledgement
  - source_hash_manifest
  - coverage_audit_by_symbol_and_day
caveats:
  - public but not zero-cost
  - data completeness must be independently audited
```

### 6.4 Venue symbol map row

```yaml
hyperliquid_coin: SOL
as_of_date: "2026-06-22"
canonical_base_asset: SOL
symbols:
  hyperliquid_perp: SOL
  binance_usdm: SOLUSDT
  binance_spot: SOLUSDT
  bybit_linear: SOLUSDT
  okx_swap: SOL-USDT-SWAP
  bitget_mix: SOLUSDT
  mexc_contract: SOL_USDT
  gate_futures: SOL_USDT
  kucoin_futures: SOLUSDTM
  htx_swap: SOL-USDT
  dydx: SOL-USD
  coinbase_spot: SOL-USD
  kraken_spot: SOL/USD
  pyth_feed: Crypto.SOL/USD
status:
  hyperliquid_liquid_as_of: true
  above_day_notional_threshold: true
  external_mapping_verified: pending
provenance:
  hyperliquid_universe_snapshot_ref: manifests/universe/...
  external_exchange_info_refs: []
```

### 6.5 Raw source manifest

```yaml
manifest_type: raw_source_manifest
source_id: hyperliquid_info_funding_history
venue: hyperliquid
family: funding
symbol: BTC
request:
  endpoint: /info
  payload_type: fundingHistory
  start_time_ms: 1704067200000
  end_time_ms: 1704153600000
response:
  raw_path: raw/venue=hyperliquid/source=hyperliquid_info_funding_history/family=funding/symbol=BTC/date=2024-01-01/page=000001.json
  raw_sha256: ...
  row_count: 24
  byte_count: ...
  downloaded_at_utc: ...
quality:
  parser_version: ...
  duplicate_count: 0
  gap_count: 0
  skipped_row_count: 0
```

### 6.6 Coverage report

```yaml
manifest_type: data_family_coverage_report
universe_snapshot_ref: manifests/universe/hyperliquid_asof_2026-06-22.json
symbol: BTC
family: trades
venue: hyperliquid
source_ids:
  - hyperliquid_ws_trades
coverage_window:
  start: "2026-06-22T00:00:00Z"
  end: "2026-06-22T23:59:59Z"
expected_buckets:
  bucket_seconds: 60
  count: 1440
observed_buckets: 1438
coverage_ratio: 0.9986
missing_buckets:
  - "2026-06-22T04:11:00Z"
  - "2026-06-22T04:12:00Z"
accepted_for_research_reporting: false
reason:
  - forward_capture_segment_only
  - not_full_2024_plus_window
```

## 7. Milestone roadmap

### M0 — Roadmap, registry contract, and safety gate

Purpose: Create the planning artifacts and schema contracts before writing collectors.

Outputs:

```text
docs/roadmaps/V2_HYPERLIQUID_DATA_VENUE_ROADMAP.md
configs/data_sources/v2_source_registry.schema.json
configs/data_sources/v2_symbol_map.schema.json
docs/contracts/data_source_registry_contract.md
docs/contracts/data_family_coverage_contract.md
```

Implementation tasks:

1. Add JSON/YAML schema for source registry entries.
2. Add JSON/YAML schema for symbol maps.
3. Add a coverage-report schema with per-family coverage ratios.
4. Add no-touch validation notes: no live/order/sizing/runtime/promotion paths.
5. Add fixtures for one source entry and one symbol map row.

Definition of done:

- Schemas validate sample registry and symbol map fixtures.
- Source registry requires `cost_class`, `native_to_hyperliquid`, `auth_required`, `paid_required`, `data_families`, and `research_role`.
- Registry rejects `paid_or_keyed` sources by default.
- Quarantined requester-pays sources cannot be marked strict-zero-dollar allowed.

### M1 — Hyperliquid as-of universe snapshots

Purpose: Build the daily universe snapshot that drives all downstream collection.

Collector name proposal:

```text
hyperliquid_universe_snapshot
```

Primary endpoint families:

```text
/info meta
/info metaAndAssetCtxs
/info allPerpMetas
```

Raw outputs:

```text
raw/venue=hyperliquid/source=hyperliquid_info_meta_asset_ctxs/family=universe/date=<date>/payload.json
manifests/universe/hyperliquid_asof_<date>.json
```

Silver outputs:

```text
silver/asset_contexts/venue=hyperliquid/date=<date>/asset_contexts.parquet
silver/universe_snapshots/venue=hyperliquid/date=<date>/universe.parquet
```

Selection rules:

```yaml
venue: hyperliquid
market_type: perpetual
min_day_notional_usd: 5000000
selection_mode: as_of
coverage_min: 0.98
earliest_reported_backtest_start: "2024-01-01"
minimum_usable_months: 6
preferred_usable_months: 12
lockbox_policy: dynamic_full_calendar_months
```

Practical details:

- Store all raw API responses before parsing.
- Preserve Hyperliquid coin names exactly as received.
- Add `canonical_base_asset` only after symbol-map resolution.
- Store `dayNtlVlm`, `markPx`, `oraclePx`, `midPx`, `funding`, `openInterest`, `premium`, and any impact-price fields when available.
- Record assets below threshold with exclusion reason instead of silently dropping them.
- Generate both current snapshot and immutable `as_of_date` snapshot IDs.

Definition of done:

- Daily universe snapshot can be produced without credentials.
- Assets above and below threshold are both represented.
- BTC/ETH are present as fixtures/reference instruments when listed, but the universe is not limited to BTC/ETH.
- Snapshot rows include raw response SHA-256 and parser version.

### M2 — Cross-venue symbol map resolver

Purpose: Resolve Hyperliquid coins to equivalent symbols on free/public external venues.

Collector name proposal:

```text
cross_venue_symbol_map_refresh
```

Sources:

```text
Hyperliquid universe snapshot
Binance exchangeInfo and Binance Vision path probes
Bybit instruments-info
OKX instruments
Bitget contracts
MEXC contract detail
Gate futures contracts
KuCoin futures contracts
HTX swap contract info
dYdX markets
Coinbase products
Kraken asset pairs
Pyth feed metadata
DexScreener/GeckoTerminal pair search
```

Practical details:

- Start with deterministic mappings for majors, then add probe-based verification for alts.
- Do not assume every Hyperliquid coin has a Binance/Bybit/OKX equivalent.
- Store aliases, remaps, base-token collisions, quote currency, contract type, and delisting status.
- Keep mapping status per venue: `verified`, `missing`, `ambiguous`, `delisted`, `not_checked`, `manual_review_required`.
- Do not use spot symbols as perpetual symbols. Store separate `market_type`.

Definition of done:

- Symbol map exists for every liquid Hyperliquid asset in the selected universe.
- Missing external venues are explicit gaps, not failures.
- Ambiguous mappings block downstream external backfill for that venue/symbol pair.

### M3 — Binance Vision historical backbone

Purpose: Build the strongest zero-cost external history backbone for overlapping symbols.

Source IDs:

```text
binance_vision_usdm_trades
binance_vision_usdm_agg_trades
binance_vision_usdm_klines
binance_vision_spot_trades
binance_vision_spot_agg_trades
binance_vision_spot_klines
```

Path probes:

```text
https://data.binance.vision/data/futures/um/daily/trades/<SYMBOL>/<SYMBOL>-trades-<YYYY-MM-DD>.zip
https://data.binance.vision/data/futures/um/daily/aggTrades/<SYMBOL>/<SYMBOL>-aggTrades-<YYYY-MM-DD>.zip
https://data.binance.vision/data/futures/um/daily/klines/<SYMBOL>/1m/<SYMBOL>-1m-<YYYY-MM-DD>.zip
https://data.binance.vision/data/spot/daily/trades/<SYMBOL>/<SYMBOL>-trades-<YYYY-MM-DD>.zip
https://data.binance.vision/data/spot/daily/aggTrades/<SYMBOL>/<SYMBOL>-aggTrades-<YYYY-MM-DD>.zip
https://data.binance.vision/data/spot/daily/klines/<SYMBOL>/1m/<SYMBOL>-1m-<YYYY-MM-DD>.zip
```

Implementation tasks:

1. Probe availability per mapped symbol/date/family.
2. Download daily first; optionally monthly for long backfills after daily logic is proven.
3. Download and verify checksum files where present.
4. Parse to bronze schemas preserving Binance-native IDs and fields.
5. Normalize to silver trades, aggTrades, and candles.
6. Reconstruct 1m candles from trades/aggTrades and compare to Binance klines.
7. Generate per-symbol/day coverage reports.

Quality checks:

- checksum match when checksum exists;
- ZIP parse success;
- monotonic timestamp validation;
- duplicate trade ID or aggTrade ID count;
- candle interval alignment;
- reconstructed OHLCV vs kline tolerance;
- missing day and partial-day detection;
- symbol listing-date and delisting handling.

Definition of done:

- For each Hyperliquid liquid asset with Binance USDM mapping, the archive knows which dates have trades, aggTrades, and 1m klines since 2024-01-01.
- Missing Binance data is recorded as coverage gap, not silently skipped.
- Binance data is always marked `native_to_hyperliquid=false`.

### M4 — Binance public derivatives context

Purpose: Add funding, open interest, mark/index/premium, taker buy/sell, and long/short ratio context from zero-cost public endpoints.

Source ID:

```text
binance_usdm_public_derivatives_context
```

Families:

```text
funding_rate_history
open_interest
open_interest_statistics
mark_price_klines
index_price_klines
premium_index_klines
taker_buy_sell_volume
long_short_ratios
basis
```

Implementation tasks:

1. Add paginated REST collectors with endpoint-specific limits.
2. Normalize quote/base units.
3. Align all context data to 1m/5m/hourly buckets by source granularity.
4. Add source-specific latency and publication-time fields where available.
5. Join to Binance Vision candles/trades only at silver/gold layers.

Definition of done:

- Funding and OI coverage reports exist separately from candle/trade coverage.
- Context sources never overwrite Hyperliquid-native funding or asset contexts.

### M5 — Hyperliquid native recent-window and forward capture

Purpose: Capture native Hyperliquid data that is zero-cost public, while respecting recent-window and bounded-capture limits.

Collectors:

```text
hyperliquid_funding_backfill
hyperliquid_recent_candle_snapshot
hyperliquid_l2_book_snapshot
hyperliquid_ws_trade_capture
hyperliquid_ws_bbo_capture
hyperliquid_ws_l2_book_capture
hyperliquid_ws_candle_capture
```

Practical details:

- Funding history: page by timestamp and store every raw page.
- Candle snapshot: request bounded windows only; record recent-window cap in manifest.
- L2 book API: record that response is a one-shot snapshot and limited to 20 levels per side.
- WebSocket sessions: write raw messages, subscribe/unsubscribe messages, heartbeats, reconnects, elapsed-time cap, message cap, row cap, and gap evidence.
- Every capture session should write a session report before any normalized rows are considered.

Suggested bounded WebSocket session manifest:

```yaml
manifest_type: hyperliquid_capture_session
source_id: hyperliquid_ws_trades
coin: BTC
subscription: trades
capture_mode: bounded_session
started_at_utc: ...
finished_at_utc: ...
elapsed_seconds: 900
message_count: 12000
row_count: 11870
heartbeat_count: 30
reconnect_count: 0
gap_events: []
continuous_capture: false
accepted_historical_coverage_proof: false
raw_capture_path: raw/venue=hyperliquid/source=hyperliquid_ws_trades/family=trades/symbol=BTC/date=...
raw_sha256: ...
```

Definition of done:

- Forward capture can run for a bounded session and produce raw/bronze/silver rows plus quality report.
- Coverage reports explicitly say bounded sessions are not full historical coverage proof.
- No collector opens streams unless its source registry entry allows the exact public WebSocket source.

### M6 — Optional Hyperliquid official archive intake gate

Purpose: Define the manual gate for native historical L2 and fill/trade replay from public requester-pays files. This is optional and disabled by default under strict-zero-dollar mode.

Sources:

```text
hyperliquid_official_s3_l2_book
hyperliquid_official_s3_asset_ctxs
hyperliquid_official_s3_node_fills_by_block
hyperliquid_official_s3_node_fills
hyperliquid_official_s3_node_trades
```

Packet gate requirements:

1. Explicitly state that the source is `public_requester_pays_transfer`.
2. Require operator acknowledgement before any transfer.
3. Preserve native files or decompressed JSON/JSONL under raw archive with SHA-256.
4. Classify official dataset as one of the supported native datasets.
5. Reject unsupported official candle/OHLCV claims before archive writes.
6. Produce coverage audits by coin/date/hour/family.
7. Keep `accepted_under_strict_free=false` in all manifests.

Definition of done:

- In strict-zero-dollar mode, these jobs fail closed before download.
- In explicit requester-pays mode, jobs can ingest trusted local decompressed files without adding credentials or secrets.
- Native fill/trade reconstruction is provenance-backed and coverage-audited before use in research panels.

### M7 — External derivative gap-fillers

Purpose: Improve coverage for Hyperliquid alts and cross-venue orderflow/context beyond Binance.

Implementation order:

1. Bybit public market data and free historical trade download verification.
2. OKX public market data: historical candles, history trades, order book, funding, OI.
3. MEXC contract public market: contract detail, depth, depth commits, klines, deals, funding.
4. Bitget Mix public market: candles, funding, OI, depth, trades where endpoint limits allow.
5. Gate futures public market.
6. KuCoin futures public market and offline-data verification.
7. HTX swap public market.
8. dYdX indexer for CLOB-perp comparison.
9. Deribit for major-asset derivatives context.

For every venue:

- Add a source registry entry first.
- Add symbol-map verification before downloading historical data.
- Add endpoint-specific page/window/rate limits to source registry.
- Store raw request/response files.
- Normalize to shared schemas only after raw manifests pass validation.
- Emit `native_to_hyperliquid=false`.
- Emit `research_role=external_comparison`, `external_orderflow_proxy`, or `spot_or_oracle_context`.

Definition of done:

- Each venue can produce an availability matrix before heavy backfill.
- Each venue has a small smoke symbol/date range fixture.
- Coverage reports identify exactly which assets/families the venue improves.

### M8 — Reconstruction and feature panels

Purpose: Convert raw/silver family archives into joined research panels without hiding provenance.

Reconstruction jobs:

```text
reconstruct_bars_from_trades
reconstruct_vwap_and_flow_features
reconstruct_bbo_spread_features
reconstruct_l2_depth_features
reconstruct_funding_oi_features
reconstruct_cross_venue_basis_features
build_gold_research_panel
```

Bar reconstruction rules:

- Prefer Hyperliquid-native trades/fills when available.
- If Hyperliquid-native trades/fills are unavailable, use external venue bars/orderflow only as external comparison/proxy columns.
- Never relabel Binance/Bybit/OKX/etc. rows as Hyperliquid trades.
- Store both source-native candles and reconstructed candles where both exist.
- Compare reconstructed OHLCV against source-native klines and flag tolerance breaches.

Example gold columns:

```text
ts
hyperliquid_coin
hl_mid_px
hl_mark_px
hl_oracle_px
hl_funding_rate
hl_open_interest
hl_day_notional_usd
hl_bbo_spread_bps
hl_l2_depth_5bps_usd
hl_trade_buy_volume_usd
hl_trade_sell_volume_usd
hl_trade_imbalance
binance_usdm_close
binance_usdm_vwap
binance_usdm_taker_imbalance
binance_usdm_open_interest
binance_usdm_funding_rate
okx_swap_close
bybit_linear_close
cross_venue_mid_dispersion_bps
spot_reference_close
pyth_oracle_px
coverage_flag_candles_1m
coverage_flag_trades
coverage_flag_funding
coverage_flag_l2
lockbox_excluded
```

Definition of done:

- Gold panels include source refs and coverage refs, not just values.
- Missing families remain nullable with explicit coverage flags.
- Feature generation fails closed when required coverage gates are not met.

### M9 — Data-family coverage audits and research gates

Purpose: Make coverage explicit by asset, venue, family, and time window.

Coverage families:

```text
universe_snapshot
asset_contexts
funding
candles_1m
trades
bbo
l2_snapshots
open_interest
liquidations
spot_oracle_context
```

Coverage audit rules:

- `candles_1m`: expected every minute in active listed periods.
- `trades`: coverage measured by time buckets and source continuity, not expected one row per bucket for illiquid assets.
- `funding`: expected at source-native funding intervals.
- `asset_contexts`: expected at snapshot cadence chosen by the collector.
- `bbo/l2`: coverage measured by capture/session windows and heartbeat continuity; do not treat sparse snapshots as continuous history.
- `external_proxy`: may satisfy cross-venue context coverage but not Hyperliquid-native execution truth.

Research-reporting gate:

```yaml
required_for_bar_research:
  - as_of_hyperliquid_universe_snapshot
  - symbol_map_snapshot
  - source_registry_snapshot
  - candles_or_reconstructed_bars_coverage >= 0.98
  - funding_coverage >= 0.98 where funding is used in net returns
  - cost_spread_slippage_impact_model_refs
  - lockbox_exclusion_proof
  - archive_snapshot_ref
  - failed_and_rejected_runs_logged
required_labels:
  - native_hyperliquid
  - external_comparison
  - external_proxy
  - diagnostic_sample
blocked_claims:
  - external venue data as Hyperliquid-native fills
  - recent API snapshots as six-month historical coverage
  - bounded WebSocket sessions as continuous historical archive
  - requester-pays official data as strict-zero-dollar data
```

Definition of done:

- Coverage reports can explain why each asset/family is accepted, rejected, or diagnostic-only.
- Audit outputs surface missing families as blocker evidence.
- No result is hidden because a source is missing; missing source data becomes visible evidence.

## 8. Implementation packet backlog

Suggested work packets:

| Packet | Title | Primary outputs | Validation |
| --- | --- | --- | --- |
| `DATA-001` | Source registry and cost-class schema | registry schema, sample entries | schema tests, paid/keyed rejection |
| `DATA-002` | Symbol-map schema and resolver scaffold | symbol map schema, mapping fixtures | ambiguous/missing mapping tests |
| `DATA-003` | Hyperliquid universe snapshot collector | raw universe payloads, as-of snapshots | threshold, raw hash, exclusion tests |
| `DATA-004` | Binance Vision availability scanner | source availability matrix | URL probe fixtures, checksum path tests |
| `DATA-005` | Binance Vision downloader/parser | raw/bronze/silver trades, aggTrades, klines | checksum, parse, duplicate, gap tests |
| `DATA-006` | Binance REST derivatives context | funding/OI/mark/index/premium/taker data | page-limit and coverage tests |
| `DATA-007` | Hyperliquid funding/recent candle/L2 collectors | raw/bronze/silver funding, recent candles, L2 snapshots | recent-window caveat tests |
| `DATA-008` | Hyperliquid bounded WS capture | trades/BBO/L2/candle capture sessions | heartbeat, reconnect, gap tests |
| `DATA-009` | Requester-pays official archive gate | disabled-by-default official archive intake | strict-zero-dollar fail-closed tests |
| `DATA-010` | Bybit/OKX gap-fillers | registry entries, smoke collectors | endpoint limit and mapping tests |
| `DATA-011` | MEXC/Bitget/Gate/KuCoin/HTX fillers | registry entries, smoke collectors | per-symbol availability matrix tests |
| `DATA-012` | dYdX/Deribit/reference venues | context collectors | overlap and context-only tests |
| `DATA-013` | Spot/oracle/on-chain context | Coinbase/Kraken/Pyth/DefiLlama/DexScreener/GeckoTerminal context | context-only labeling tests |
| `DATA-014` | Bar reconstruction from trades | reconstructed candles and comparison reports | OHLCV tolerance tests |
| `DATA-015` | Orderflow feature reconstruction | trade/BBO/L2/funding/OI features | provenance and null-coverage tests |
| `DATA-016` | Data-family coverage audit | coverage manifests | 0.98 coverage and lockbox tests |
| `DATA-017` | Gold research panel builder | feature panels with refs | fail-closed missing evidence tests |
| `DATA-018` | Runbooks and operator docs | source runbooks | docs-only boundary check |

## 9. First practical build sequence

The fastest useful sequence is:

1. Add source registry and symbol-map schemas.
2. Build Hyperliquid universe snapshots.
3. Build Binance Vision availability matrix for current liquid Hyperliquid universe.
4. Backfill Binance Vision klines/trades/aggTrades for 2024-01-01+ where symbols exist.
5. Add Binance funding/OI/mark/index/premium/taker context.
6. Add Hyperliquid funding history and recent snapshots.
7. Add bounded Hyperliquid WebSocket forward capture.
8. Add coverage audits and gold panel assembly.
9. Add Bybit and OKX only after Binance + Hyperliquid paths are stable.
10. Add MEXC/Bitget/Gate/KuCoin/HTX only for assets still missing external derivative coverage.
11. Add spot/oracle/on-chain context after derivative data exists.
12. Consider Hyperliquid official requester-pays archive only if strict-zero-dollar mode is explicitly relaxed in a separate packet.

## 10. Smoke-test universe

Do not hardcode the product universe, but start development with a small smoke universe:

```yaml
smoke_universe_policy:
  fixed_reference:
    - BTC
    - ETH
    - SOL
  dynamic_liquid_alts:
    count: 2
    selection: highest_day_notional_from_latest_hyperliquid_asof_snapshot_excluding_fixed_reference
  below_threshold_negative_control:
    count: 1
    selection: one_current_hyperliquid_perp_below_min_day_notional_when_available
```

Purpose:

- BTC/ETH/SOL are likely to have broad external coverage.
- Dynamic alts test symbol mapping and survivorship handling.
- A below-threshold negative control proves exclusion reasons are recorded.

## 11. Quality and failure handling

Every collector should fail closed before writing normalized data when:

- source registry entry is missing;
- `cost_class` is not allowed under current mode;
- symbol map status is `ambiguous` or `manual_review_required`;
- raw download lacks source URL/path and hash metadata;
- parsed rows violate required schema;
- timestamps cannot be normalized to UTC;
- interval rows are misaligned;
- file path includes secret-like or unsafe components;
- API page cap is exhausted before full requested window;
- checksum verification fails where checksum is expected;
- endpoint returns a newer schema that parser cannot classify.

Every collector should write explicit blocker evidence when:

- source has no coverage for a symbol/date;
- venue delisted or had not listed the symbol yet;
- endpoint lookback is too short;
- rate limit prevents completion;
- Hyperliquid recent-window endpoints are requested for old history;
- official requester-pays sources are disabled by strict-free mode.

## 12. Open decisions

1. Should strict-zero-dollar mode permanently exclude Hyperliquid official requester-pays archives, or should a separate manually approved mode allow them for native historical orderflow reconstruction?
2. What is the maximum local storage budget for raw Binance Vision trades across the liquid Hyperliquid universe?
3. Should L2 order book history be required for any research panel, or used only for slippage/impact model calibration when coverage exists?
4. What minimum external venue overlap is required before a Hyperliquid asset enters broad research panels?
5. Should all external sources be collected for every asset, or should the system stop after enough coverage is reached?
6. What cadence should the as-of universe snapshot use: daily UTC close, hourly, or both?
7. Should on-chain/DEX context be required only for long-tail alts, or collected for all listed tokens where available?

## 13. Source references checked for this roadmap

- Hyperliquid historical data: https://hyperliquid.gitbook.io/hyperliquid-docs/historical-data
- Hyperliquid info endpoint: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint
- Hyperliquid WebSocket subscriptions: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions
- Binance public data archive: https://github.com/binance/binance-public-data
- Binance USD-M futures market data REST: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api
- Bybit V5 market API: https://bybit-exchange.github.io/docs/v5/market/kline
- OKX API V5 documentation: https://app.okx.com/docs-v5/en/
- Bitget futures market API: https://www.bitget.com/api-doc/contract/market/Get-Candle-Data
- MEXC contract API: https://mexcdevelop.github.io/apidocs/contract_v1_en/
- Gate.io API V4: https://www.gate.io/docs/developers/apiv4/en/
- KuCoin futures market data API: https://www.kucoin.com/docs-new/rest/futures-trading/market-data/get-klines
- Pyth Hermes: https://docs.pyth.network/price-feeds/core/api-instances-and-providers/hermes
- DefiLlama API: https://api-docs.defillama.com/
- DexScreener API: https://docs.dexscreener.com/api/reference
- GeckoTerminal API: https://www.geckoterminal.com/dex-api
