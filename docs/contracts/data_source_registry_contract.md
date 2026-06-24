# Data Source Registry Contract

Status: v2 data-venue roadmap foundation
Audit IDs: `V2-AUD-DATASRC-001`, `V2-AUD-DATASRC-002`, `V2-AUD-DATASRC-004`, `V2-AUD-DATASRC-005`, `V2-AUD-DATASRC-006`, `V2-AUD-DATASRC-007`, `V2-AUD-DATASRC-008`, `V2-AUD-DATASRC-009`, `V2-AUD-DATASRC-010`, `V2-AUD-DATASRC-011`, `V2-AUD-DATASRC-012`, `V2-AUD-DATASRC-013`, `V2-AUD-DATASRC-014`, `V2-AUD-DATASRC-015`, `V2-AUD-DATASRC-016`, `V2-AUD-DATASRC-017`, `V2-AUD-DATASRC-018`, `V2-AUD-DATASRC-019`, `V2-AUD-DATASRC-020`, `V2-AUD-DATASRC-021`, `V2-AUD-DATASRC-022`, `V2-AUD-DATASRC-023`, `V2-AUD-DATASRC-024`, `V2-AUD-DATASRC-025`, `V2-AUD-DATASRC-026`, `V2-AUD-DATASRC-027`, `V2-AUD-DATASRC-028`, `V2-AUD-DATASRC-029`, `V2-AUD-DATASRC-030`, `V2-AUD-DATASRC-031`, `V2-AUD-DATASRC-032`, `V2-AUD-DATASRC-033`, `V2-AUD-DATASRC-034`, `V2-AUD-DATASRC-035`, `V2-AUD-DATASRC-036`, `V2-AUD-DATASRC-037`, `V2-AUD-DATASRC-038`, `V2-AUD-DATASRC-039`, `V2-AUD-DATASRC-040`, `V2-AUD-DATASRC-041`, `V2-AUD-DATASRC-042`
Source roadmap: `docs/roadmaps/V2_HYPERLIQUID_DATA_VENUE_ROADMAP.md`

## Purpose

The v2 source registry describes every free/public, diagnostic, requester-pays,
or paid/keyed data source before any collector may trust it. It prevents
collectors from treating external venues as Hyperliquid-native evidence,
prevents paid/keyed or requester-pays sources from entering strict-zero-dollar
runs by omission, and records the provenance fields required for raw archive
intake.

## Schemas

Primary code schemas:

- `SourceRegistryEntry`
- `SourceRegistrySnapshot`
- `CostClass`
- `VenueSymbolMapRow`
- `VenueSymbolRef`
- `SymbolMapSnapshot`
- `BinanceVisionAvailabilityManifest`
- `BinanceVisionAvailabilityRow`
- `BinanceVisionDownloadResult`
- `BinanceVisionDownloadStatus`
- `BinanceVisionDailyBackfillResult`
- `BinanceVisionBackfillBatchResult`
- `BinanceVisionBackfillStatus`
- `BinanceVisionParseResult`
- `BinanceVisionParsedDataRow`
- `BinanceVisionArchiveIngestResult`
- `BinanceVisionBarComparisonReport`
- `BinanceDerivativesContextArchiveIngestResult`
- `BinanceDerivativesContextArchiveIngestStatus`
- `BinanceDerivativesContextBackfillResult`
- `BinanceDerivativesContextBackfillStatus`
- `BinanceDerivativesContextEndpointSpec`
- `BinanceDerivativesContextFetchResult`
- `BinanceDerivativesContextFetchStatus`
- `BinanceDerivativesContextFamily`
- `BinanceDerivativesContextGetResult`
- `BinanceDerivativesContextNormalizedRow`
- `BinanceDerivativesContextPageResult`
- `BinanceDerivativesContextPageStatus`
- `BinanceDerivativesContextRequest`
- `BybitOkxAvailabilityManifest`
- `BybitOkxAvailabilityRequest`
- `BybitOkxAvailabilityRow`
- `BybitOkxAvailabilityStatus`
- `BybitOkxAvailabilityWriteResult`
- `BybitOkxEndpointSpec`
- `BybitOkxFetchResult`
- `BybitOkxFetchStatus`
- `BybitOkxGetResult`
- `BybitOkxNormalizedRow`
- `AltDerivativesAvailabilityManifest`
- `AltDerivativesAvailabilityRequest`
- `AltDerivativesAvailabilityRow`
- `AltDerivativesAvailabilityStatus`
- `AltDerivativesAvailabilityWriteResult`
- `AltDerivativesEndpointSpec`
- `AltDerivativesFetchResult`
- `AltDerivativesFetchStatus`
- `AltDerivativesGetResult`
- `AltDerivativesNormalizedRow`
- `ReferenceDerivativesAvailabilityManifest`
- `ReferenceDerivativesAvailabilityRequest`
- `ReferenceDerivativesAvailabilityRow`
- `ReferenceDerivativesAvailabilityStatus`
- `ReferenceDerivativesAvailabilityWriteResult`
- `ReferenceDerivativesEndpointSpec`
- `ReferenceDerivativesFetchResult`
- `ReferenceDerivativesFetchStatus`
- `ReferenceDerivativesGetResult`
- `ReferenceDerivativesNormalizedRow`
- `SpotOracleContextAvailabilityManifest`
- `SpotOracleContextAvailabilityRequest`
- `SpotOracleContextAvailabilityRow`
- `SpotOracleContextAvailabilityStatus`
- `SpotOracleContextAvailabilityWriteResult`
- `SpotOracleContextEndpointSpec`
- `SpotOracleContextFetchResult`
- `SpotOracleContextFetchStatus`
- `SpotOracleContextGetResult`
- `SpotOracleContextNormalizedRow`
- `TradeBarInputRow`
- `ReconstructedTradeBarRow`
- `TradeBarReconstructionReport`
- `SourceNativeBarInputRow`
- `ReconstructedBarComparisonRow`
- `ReconstructedBarComparisonReport`
- `OrderflowFeatureRow`
- `OrderflowFeatureReport`
- `DerivativesContextFeatureInputRow`
- `DerivativesContextFeatureRow`
- `DerivativesContextFeatureReport`
- `BBOFeatureInputRow`
- `BBOFeatureRow`
- `BBOFeatureReport`
- `L2DepthFeatureInputRow`
- `L2DepthFeatureRow`
- `L2DepthFeatureReport`
- `CrossVenuePriceInputRow`
- `CrossVenueBasisFeatureRow`
- `CrossVenueBasisFeatureReport`
- `SymbolProbeResult`
- `resolve_symbol_map_for_coin`
- `resolve_symbol_maps_from_universe_rows`
- `write_universe_data_source_manifests`
- `write_binance_vision_availability_manifest`
- `download_binance_vision_availability_row_to_cache`
- `run_binance_vision_daily_backfill`
- `run_binance_vision_backfill_batch`
- `parse_binance_vision_zip_bytes`
- `ingest_binance_vision_zip_bytes_to_archive`
- `compare_binance_vision_reconstructed_bars`
- `build_binance_vision_data_family_coverage_report`
- `build_binance_derivatives_context_coverage_report`
- `build_binance_derivatives_context_request`
- `binance_derivatives_context_spec`
- `build_bybit_okx_availability_request`
- `fetch_bybit_okx_public_market_request`
- `bybit_okx_endpoint_spec`
- `bybit_okx_normalized_row_hash`
- `build_alt_derivatives_availability_request`
- `alt_derivatives_endpoint_spec`
- `build_reference_derivatives_availability_request`
- `fetch_reference_derivatives_public_market_request`
- `reference_derivatives_endpoint_spec`
- `reference_derivatives_normalized_row_hash`
- `write_reference_derivatives_availability_manifest`
- `build_spot_oracle_context_availability_request`
- `fetch_spot_oracle_context_public_market_request`
- `spot_oracle_context_endpoint_spec`
- `spot_oracle_context_normalized_row_hash`
- `write_spot_oracle_context_availability_manifest`
- `reconstruct_trade_bars_from_rows`
- `compare_reconstructed_trade_bars_to_source_bars`
- `reconstructed_trade_bar_row_hash`
- `reconstructed_bar_comparison_report_id_for`
- `trade_bar_reconstruction_report_id_for`
- `reconstruct_orderflow_features_from_trades`
- `orderflow_feature_row_hash`
- `orderflow_feature_report_id_for`
- `reconstruct_funding_oi_features_from_context_rows`
- `derivatives_context_feature_row_hash`
- `derivatives_context_feature_report_id_for`
- `reconstruct_bbo_spread_features_from_rows`
- `bbo_feature_row_hash`
- `bbo_feature_report_id_for`
- `reconstruct_l2_depth_features_from_rows`
- `l2_depth_feature_row_hash`
- `l2_depth_feature_report_id_for`
- `reconstruct_cross_venue_basis_features_from_prices`
- `cross_venue_basis_feature_row_hash`
- `cross_venue_basis_feature_report_id_for`
- `fetch_alt_derivatives_public_market_request`
- `alt_derivatives_normalized_row_hash`
- `write_alt_derivatives_availability_manifest`
- `fetch_binance_derivatives_context_request`
- `fetch_binance_derivatives_context_pages`
- `ingest_binance_derivatives_context_pages_to_archive`
- `run_binance_derivatives_context_backfill`
- `write_bybit_okx_availability_manifest`

Checked JSON schemas and sample fixtures:

- `configs/data_sources/v2_source_registry.schema.json`
- `configs/data_sources/v2_symbol_map.schema.json`
- `configs/data_sources/samples/source_registry_bitget_public_mix_market.json`
- `configs/data_sources/samples/source_registry_bybit_public_market.json`
- `configs/data_sources/samples/source_registry_coinbase_spot_public.json`
- `configs/data_sources/samples/source_registry_defillama_public.json`
- `configs/data_sources/samples/source_registry_deribit_public.json`
- `configs/data_sources/samples/source_registry_dexscreener_public.json`
- `configs/data_sources/samples/source_registry_dydx_indexer_public.json`
- `configs/data_sources/samples/source_registry_geckoterminal_public.json`
- `configs/data_sources/samples/source_registry_binance_vision_usdm_trades.json`
- `configs/data_sources/samples/source_registry_binance_vision_usdm_agg_trades.json`
- `configs/data_sources/samples/source_registry_binance_vision_usdm_klines.json`
- `configs/data_sources/samples/source_registry_binance_vision_spot_trades.json`
- `configs/data_sources/samples/source_registry_binance_vision_spot_agg_trades.json`
- `configs/data_sources/samples/source_registry_binance_vision_spot_klines.json`
- `configs/data_sources/samples/source_registry_binance_usdm_public_derivatives_context.json`
- `configs/data_sources/samples/source_registry_gate_futures_public.json`
- `configs/data_sources/samples/source_registry_hyperliquid_info_candle_snapshot_recent.json`
- `configs/data_sources/samples/source_registry_hyperliquid_info_funding_history.json`
- `configs/data_sources/samples/source_registry_hyperliquid_info_l2_book_snapshot.json`
- `configs/data_sources/samples/source_registry_hyperliquid_info_meta_asset_ctxs.json`
- `configs/data_sources/samples/source_registry_hyperliquid_official_fills_quarantined.json`
- `configs/data_sources/samples/source_registry_hyperliquid_official_s3_asset_ctxs.json`
- `configs/data_sources/samples/source_registry_hyperliquid_official_s3_l2_book.json`
- `configs/data_sources/samples/source_registry_hyperliquid_official_s3_node_fills.json`
- `configs/data_sources/samples/source_registry_hyperliquid_official_s3_node_trades.json`
- `configs/data_sources/samples/source_registry_hyperliquid_ws_bbo.json`
- `configs/data_sources/samples/source_registry_hyperliquid_ws_candle.json`
- `configs/data_sources/samples/source_registry_hyperliquid_ws_l2_book.json`
- `configs/data_sources/samples/source_registry_hyperliquid_ws_trades.json`
- `configs/data_sources/samples/source_registry_htx_swap_public.json`
- `configs/data_sources/samples/source_registry_kucoin_futures_public.json`
- `configs/data_sources/samples/source_registry_kraken_spot_public.json`
- `configs/data_sources/samples/source_registry_mexc_contract_public.json`
- `configs/data_sources/samples/source_registry_okx_public_market.json`
- `configs/data_sources/samples/source_registry_pyth_hermes_public.json`
- `configs/data_sources/samples/symbol_map_sol_2026_06_22.json`

## Cost Classes

Source entries must use one of these exact classes:

| Cost class | Meaning | Strict-zero-dollar behavior |
| --- | --- | --- |
| `zero_cost_public` | Public source with no expected account, secret, paid tier, or transfer charge. | Allowed when no auth, secret, or payment is required. |
| `public_rate_limited` | Free public endpoint with documented or observed rate limits. | Allowed with backoff, retry, and page/window caps. |
| `free_sample_only` | Free sample useful for parser/schema tests only. | Diagnostic only; never accepted historical coverage proof. |
| `public_requester_pays_transfer` | Public source with requester-paid transfer or storage cost. | Quarantined and disabled under strict-zero-dollar mode. |
| `paid_or_keyed` | Paid vendor, paid tier, private credentials, or account-specific export. | Out of scope for this roadmap and rejected by default. |

## Required Registry Fields

`SourceRegistryEntry` requires:

- `source_id`
- `venue`
- `market_type`
- `native_to_hyperliquid`
- `cost_class`
- `auth_required`
- `paid_required`
- `data_families`
- `history_mode`
- `priority`
- `research_role`

Provenance requirements should include source URLs or local source refs,
download/capture timestamps, SHA-256 hashes, byte counts, row counts, checksum
refs when available, parser versions, and any page/window limits relevant to
replay.

## Strict-Free Rules

Collectors running in strict-zero-dollar mode must call
`require_strict_zero_dollar_source()` before network, file, or archive work.
That gate fails closed when:

- `cost_class` is `public_requester_pays_transfer`;
- `cost_class` is `paid_or_keyed`;
- `auth_required`, `secret_required`, or `paid_required` is true;
- `strict_zero_dollar_allowed` is false.

Requester-pays Hyperliquid official files may be described in the registry only
as quarantined sources. They must keep `strict_zero_dollar_allowed=false`,
`accepted_under_strict_free=false`, and an explicit `required_operator_gate`.

`DATA-009` requester-pays official source IDs are:

- `hyperliquid_official_s3_l2_book`
- `hyperliquid_official_s3_asset_ctxs`
- `hyperliquid_official_s3_node_fills_by_block`
- `hyperliquid_official_s3_node_fills`
- `hyperliquid_official_s3_node_trades`

All five are `public_requester_pays_transfer`, native to Hyperliquid, disabled
under strict-zero-dollar mode, and not accepted historical coverage proof. They
must retain operator gates for explicit packet scope, transfer-cost
acknowledgement, source-hash manifests, and coverage audits before any later
approved requester-pays workflow can use them.

## Hyperliquid Public REST Source Entries

`DATA-007` native public REST source entries are:

- `hyperliquid_info_funding_history`
- `hyperliquid_info_candle_snapshot_recent`
- `hyperliquid_info_l2_book_snapshot`

These entries are `zero_cost_public`, `native_to_hyperliquid=true`, and
strict-zero-dollar allowed. They support the already bounded durable collector
routes for public funding history, recent candle snapshots, and one-shot L2
book snapshots. Their provenance requirements must include raw request/response
IDs, raw payload hashes, source coin, row counts, request time, and endpoint-
specific paging or cap fields.

The entries must keep `accepted_historical_coverage_proof=false`. Funding
history is intake evidence until later archive coverage/audit gates accept a
separate snapshot. Candle snapshots remain recent-window evidence, and L2 book
snapshots remain one-shot 20-level-per-side evidence.

## Hyperliquid Public WebSocket Source Entries

`DATA-008` native public WebSocket source entries are:

- `hyperliquid_ws_trades`
- `hyperliquid_ws_bbo`
- `hyperliquid_ws_l2_book`
- `hyperliquid_ws_candle`

These entries are `zero_cost_public`, `native_to_hyperliquid=true`, and
strict-zero-dollar allowed. They support bounded public WebSocket capture only.
Collector specs must declare `source_registry_source_id` matching the exact
stream before any stream is opened, and durable outputs must preserve that
source ID with raw request/response/hash, subscription, cap, row-count,
heartbeat/session, reconnect, and gap evidence.

All public WebSocket source entries must keep
`accepted_historical_coverage_proof=false`. Bounded sessions and snapshots are
not continuous historical coverage, queue/fill realism proof, scheduler proof,
full archive readiness, candidate evidence, or promotion evidence.

## Bybit and OKX Public Market Source Entries

`DATA-010` begins with source registry entries for:

- `bybit_public_market`
- `okx_public_market`

Both entries are `public_rate_limited`, `native_to_hyperliquid=false`, and
strict-zero-dollar allowed. They are external comparison sources only. They may
cover candles, trades, BBO/order book, funding, and open-interest families only
after symbol-map verification, availability matrix output, raw request/response
preservation, and endpoint-specific pagination/rate-limit validation.

Bybit and OKX source entries must keep
`accepted_historical_coverage_proof=false`. Future collectors must not relabel
their rows as Hyperliquid-native trades, fills, funding, BBO, L2, or candles.

## Bybit and OKX Availability Matrix

`write_bybit_okx_availability_manifest()` implements the first `DATA-010`
availability-matrix foundation for `bybit_public_market` and
`okx_public_market`. It builds deterministic public REST request URLs for
checked Bybit and OKX endpoint families, requires verified symbol-map rows, and
writes metadata-only manifests under `manifests/source_availability/`.

Availability rows may be `available`, `missing`, `blocked_mapping`,
`blocked_endpoint_limit`, or `probe_error`. Recent/snapshot endpoints such as
order book or recent trades do not become historical evidence for old dates;
they are marked `blocked_endpoint_limit` until a later packet adds a suitable
historical download or cursor contract. All rows remain
`native_to_hyperliquid=false` and `accepted_historical_coverage_proof=false`.

## Bybit and OKX Smoke Fetch Normalization

`fetch_bybit_okx_public_market_request()` consumes one deterministic
Bybit/OKX availability request through an injected GET client and normalizes
fixture/injected response rows for supported date-window endpoints. Normalized
rows preserve endpoint ID, source ID, venue symbol, source timestamp, raw
fields, numeric fields, request URL, stable row hash, and research-only
boundary flags.

The smoke fetch layer is in-memory only. It does not write raw, bronze, or
silver archive rows and does not create accepted historical coverage proof.
Recent/snapshot-only endpoints are blocked before fetch.

## Alt Derivatives Public Market Source Entries

`DATA-011` begins with source registry entries for:

- `bitget_public_mix_market`
- `mexc_contract_public`
- `gate_futures_public`
- `kucoin_futures_public`
- `htx_swap_public`

All five entries are `public_rate_limited`, `native_to_hyperliquid=false`, and
strict-zero-dollar allowed. They are external comparison sources only. They
require symbol-map verification, availability-matrix output, raw request and
response preservation, and endpoint-specific pagination/rate-limit validation
before any future collector may use them.

Alt-derivatives source entries must keep
`accepted_historical_coverage_proof=false`. Future collectors must not relabel
their rows as Hyperliquid-native trades, fills, funding, BBO, L2, candles, open
interest, or liquidation events.

## Alt Derivatives Availability Matrix

`write_alt_derivatives_availability_manifest()` implements the first
`DATA-011` metadata-only availability matrix for the alt-derivatives source
entries. It builds deterministic public REST candle request URLs for Bitget,
MEXC, Gate, KuCoin, and HTX, requires verified venue symbol mappings, and
writes manifests under `manifests/source_availability/`.

Availability rows may be `available`, `missing`, `blocked_mapping`, or
`probe_error`. They preserve source ID, endpoint ID, venue key, venue symbol,
request URL, date window, response row count, endpoint-rate hint, and blocker
reasons. All rows remain `native_to_hyperliquid=false` and
`accepted_historical_coverage_proof=false`.

## Alt Derivatives Smoke Fetch Normalization

`fetch_alt_derivatives_public_market_request()` consumes one deterministic
alt-derivatives availability request through an injected GET client and
normalizes fixture/injected candle response rows for Bitget, MEXC, Gate,
KuCoin, or HTX. Normalized rows preserve endpoint ID, source ID, venue symbol,
source timestamp, raw fields, numeric fields, request URL, stable row hash, and
research-only boundary flags.

The smoke fetch layer is in-memory only. It does not write raw, bronze, or
silver archive rows and does not create accepted historical coverage proof.

## dYdX and Deribit Public Source Entries

`DATA-012` begins with source registry entries for:

- `dydx_indexer_public`
- `deribit_public`

Both entries are `public_rate_limited`, `native_to_hyperliquid=false`, and
strict-zero-dollar allowed. They are external comparison/reference context
sources only. dYdX overlap with the Hyperliquid universe must be verified
through symbol-map evidence before use; Deribit remains major-asset derivatives
context unless a later packet proves broader overlap.

dYdX and Deribit source entries must keep
`accepted_historical_coverage_proof=false`. Future collectors must not relabel
their rows as Hyperliquid-native trades, fills, funding, BBO, L2, candles, open
interest, or universe membership.

## dYdX and Deribit Availability Matrix

`write_reference_derivatives_availability_manifest()` implements the first
`DATA-012` metadata-only availability matrix for dYdX indexer candles and
Deribit public TradingView candle data. It builds deterministic public REST
request URLs, requires verified venue symbol mappings, validates strict-free
external-comparison source entries, and writes manifests under
`manifests/source_availability/`.

Availability rows may be `available`, `missing`, `blocked_mapping`, or
`probe_error`. They preserve source ID, endpoint ID, venue key, venue symbol,
request URL, date window, response row count, endpoint-rate hint, and blocker
reasons. All rows remain `native_to_hyperliquid=false` and
`accepted_historical_coverage_proof=false`.

dYdX candle probes use `/v4/candles/perpetualMarkets/{symbol}` with `1MIN`
resolution and ISO date windows. Deribit probes use
`/api/v2/public/get_tradingview_chart_data` with `BASE-PERPETUAL` instruments,
millisecond date windows, and one-minute resolution. The matrix may classify
availability from injected or public probe metadata only; it must not write
raw/bronze/silver archive rows or accepted data-family coverage.

## dYdX and Deribit Smoke Fetch Normalization

`fetch_reference_derivatives_public_market_request()` consumes one deterministic
dYdX/Deribit availability request through an injected GET client and normalizes
fixture/injected candle response rows. dYdX candle object rows and Deribit
TradingView columnar responses are converted into stable
`ReferenceDerivativesNormalizedRow` records with source ID, endpoint ID, venue
symbol, source timestamp, raw fields, numeric fields, request URL, row hash, and
research-only boundary flags.

The smoke layer returns `completed`, `empty`, `fetch_error`, or `parse_error`.
Empty/no-data payloads, venue API errors, malformed rows, bad source entries,
and historical-coverage-proof claims fail closed without archive writes. Smoke
fetch output is not raw/bronze/silver archive data and does not create accepted
historical coverage proof.

## Spot, Oracle, and On-Chain Context Source Entries

`DATA-013` begins with source registry entries for:

- `coinbase_spot_public`
- `kraken_spot_public`
- `pyth_hermes_public`
- `defillama_public`
- `dexscreener_public`
- `geckoterminal_public`

Coinbase and Kraken are strict-free public-rate-limited spot reference sources
and remain `external_comparison` only. Pyth Hermes, DefiLlama, DexScreener, and
GeckoTerminal are strict-free context/oracle sources and remain
`spot_or_oracle_context` only. All six entries must keep
`native_to_hyperliquid=false` and `accepted_historical_coverage_proof=false`.

Future context collectors must verify symbol or context mappings, preserve raw
request/response refs, record endpoint params and rate-limit metadata, and keep
spot/oracle/on-chain rows separate from Hyperliquid-native trades, fills,
funding, BBO, L2, orders, or universe membership. These entries do not create
downloads, archive rows, accepted coverage, candidate evidence, paper/live
behavior, or promotion claims.

## Spot, Oracle, and On-Chain Context Availability Matrix

`write_spot_oracle_context_availability_manifest()` implements the first
`DATA-013` metadata-only availability matrix for strict-free spot, oracle, and
on-chain context sources. It builds deterministic request URLs for Coinbase
spot candles, Kraken spot OHLC, Pyth Hermes latest prices, DefiLlama current
prices, DexScreener search, and GeckoTerminal pool search.

Availability rows may be `available`, `missing`, `blocked_mapping`, or
`probe_error`. The matrix requires verified symbol-map entries before probes,
validates spot sources as `external_comparison`, validates oracle/context
sources as `spot_or_oracle_context`, and rejects any source entry that claims
accepted historical coverage proof. Rows preserve source ID, endpoint ID,
venue key, venue symbol, request URL, date window, response row count,
endpoint-rate hint, and blocker reasons.

All rows remain `native_to_hyperliquid=false` and
`accepted_historical_coverage_proof=false`. The matrix writes metadata under
`manifests/source_availability/`; it does not download payloads into raw,
bronze, or silver archive rows and does not create accepted coverage evidence.

## Spot, Oracle, and On-Chain Context Smoke Fetch Normalization

`fetch_spot_oracle_context_public_market_request()` consumes one deterministic
DATA-013 availability request through an injected GET client and normalizes
fixture/injected response rows. Coinbase and Kraken candle rows, Pyth parsed
price rows, DefiLlama coin-price rows, DexScreener pair rows, and
GeckoTerminal pool rows are converted into generic
`SpotOracleContextNormalizedRow` records with source ID, endpoint ID, venue
symbol, optional source timestamp, raw fields, numeric fields, request URL, row
hash, and research-only boundary flags.

The smoke layer returns `completed`, `empty`, `fetch_error`, or `parse_error`.
Empty payloads, venue API errors, malformed rows, bad source entries, and
historical-coverage-proof claims fail closed without archive writes. Smoke
fetch output is not raw/bronze/silver archive data and does not create accepted
historical coverage proof.

## Universe Manifest Bridge

`write_universe_data_source_manifests()` connects recorded Hyperliquid
`UniverseSnapshotRow` records to data-source registry and symbol-map artifacts.
It writes:

- `manifests/source_registry/source_registry_<date>_<id>.json`
- `manifests/symbol_maps/symbol_map_<date>_<id>.json`

The bridge is local-only and performs no venue/API fetch. It requires one
Hyperliquid-native universe source entry, validates all source entries through
strict-zero-dollar rules, and additionally requires each entry to be accepted
under strict-free mode. Requester-pays, paid/keyed, and strict-free-unaccepted
free-sample entries fail before either manifest is written.

`SourceRegistrySnapshot` and `SymbolMapSnapshot` carry deterministic identity
hashes. Symbol-map row hashes exclude row creation timestamps so the same
universe rows, source registry entries, and probe evidence produce stable
snapshot IDs. Below-threshold or otherwise excluded universe rows remain in the
symbol-map snapshot with provenance and blocker reasons rather than being
silently dropped.

## Binance Vision Availability

`write_binance_vision_availability_manifest()` implements the `DATA-004`
availability scan only. It checks daily ZIP URLs and, when a ZIP is present,
the matching `.CHECKSUM` URL for these strict-free source IDs:

- `binance_vision_usdm_trades`
- `binance_vision_usdm_agg_trades`
- `binance_vision_usdm_klines`
- `binance_vision_spot_trades`
- `binance_vision_spot_agg_trades`
- `binance_vision_spot_klines`

The scanner requires matching strict-free `SourceRegistryEntry` rows and a
`SymbolMapSnapshot`. USD-M sources require a verified `binance_usdm` mapping;
spot sources require a verified `binance_spot` mapping. Unverified mappings are
written as `blocked_mapping` rows without URL probes. Missing ZIPs, missing
checksums, and probe errors are explicit row statuses.

The scanner writes metadata-only manifests below
`manifests/source_availability/`. It does not download archives, parse ZIPs,
write bronze/silver market data, reconstruct bars, or create accepted coverage
evidence. Binance Vision rows must keep `native_to_hyperliquid=false`.

## Binance Vision Downloader Cache

`download_binance_vision_availability_row_to_cache()` consumes one
`BinanceVisionAvailabilityRow` and writes deterministic local cache files below
the archive root for available Binance Vision ZIP payloads and optional
checksum payloads. The downloader has an injectable GET client so tests and
bounded jobs can run offline/fake transports without changing production
semantics.

`BinanceVisionDownloadResult` records download status, cache refs, ZIP SHA-256,
checksum payload hash, expected checksum, byte counts, cache-hit status,
max-byte cap, source registry and symbol-map refs, cost class, blocker reasons,
and full research-only boundary flags. Non-available rows, unsupported cost
classes, missing URLs, HTTP errors, max-byte violations, and checksum mismatch
fail closed as blocker metadata. Cache hits reuse local bytes without a
network call and keep the same stable download identity as the original
downloaded payload.

The downloader cache does not parse ZIP bytes, write bronze/silver rows, create
coverage reports, run backtests, or mark evidence Hyperliquid-native.

## Binance Vision Daily Backfill Orchestration

`run_binance_vision_daily_backfill()` chains one target availability row
through download/cache, parser, local archive ingest, optional reconstructed-bar
comparison, and data-family coverage report writing. The helper writes
coverage JSON under `manifests/coverage_reports/` and returns a
`BinanceVisionDailyBackfillResult` containing the target download manifest ref,
target parse hash, target ingest ID, optional comparison download/parse/report
IDs, coverage report ref, acceptance flag, and blocker reasons.

The helper is a bounded local orchestration unit, not a durable worker queue or
full backfill planner. It accepts an injected GET client and an optional
archive snapshot ref. Missing downloads, checksum mismatch, parser failures,
ingest failures, missing comparison evidence, failed reconstructed-bar
comparison, missing archive snapshot refs, and coverage blockers remain
explicit result metadata.

## Binance Vision Backfill Batch Coordination

`run_binance_vision_backfill_batch()` consumes a
`BinanceVisionAvailabilityManifest`, selects rows for one target source ID,
optionally matches comparison rows by `(binance_symbol, probe_date)`, runs the
daily backfill helper per selected row, and writes a batch manifest under
`manifests/binance_vision_backfills/`.

`BinanceVisionBackfillBatchResult` records the availability manifest ID,
target and comparison source IDs, max-row cap, daily result IDs, embedded daily
results, completed/blocked/accepted counts, and aggregate blocker reasons. It
is bounded local coordination only; durable worker scheduling and unattended
multi-day operational policy remain separate work.

## Binance USD-M Derivatives Context Foundation

`binance_usdm_public_derivatives_context` is a strict-free,
public-rate-limited external context source for `DATA-006`. Its source-registry
fixture is non-Hyperliquid-native, does not require auth/secrets/payment, and
does not claim accepted historical coverage proof until endpoint-specific
coverage reports exist.

`build_binance_derivatives_context_request()` is an offline request builder
only. It records deterministic endpoint, parameter, limit, rate-limit, and
official-doc metadata for:

- `funding_rate_history`;
- `open_interest`;
- `open_interest_statistics`;
- `mark_price_klines`;
- `index_price_klines`;
- `premium_index_klines`;
- `taker_buy_sell_volume`;
- `long_short_ratios`;
- `basis`.

The builder fails closed on unknown families, missing required interval or
period values, unsupported time ranges, unsupported contract types, and
endpoint-specific limit overages. The request artifact keeps full
research-only boundary flags and never marks Binance context as
Hyperliquid-native. Fetching, pagination, normalization, archive writes, and
funding/OI coverage acceptance remain later packets.

## Binance USD-M Derivatives Fetch Normalize

`fetch_binance_derivatives_context_request()` consumes one prebuilt
`BinanceDerivativesContextRequest`, calls an injectable GET client, and returns
`BinanceDerivativesContextFetchResult`. The result records HTTP status,
headers, response SHA-256, byte count, raw row count, normalized row count,
stable normalized-row hash, blocker reasons, and full research-only boundary
flags.

`BinanceDerivativesContextNormalizedRow` preserves the source family, venue
symbol, source timestamp, publication timestamp, interval or period,
bucket-seconds alignment, raw fields, normalized numeric fields, and unit
annotations. Funding, OI, OI statistics, mark/index/premium klines, taker
buy/sell volume, long/short ratios, and basis use generic normalized fields so
later archive writers can specialize schemas without losing endpoint
provenance.

HTTP errors, explicit fetch errors, oversized responses, invalid JSON, invalid
row shapes, and invalid timestamps become blocked/error fetch results rather
than hidden skips. This layer performs no pagination, archive writes, coverage
acceptance, worker scheduling, or Hyperliquid-native relabeling.

## Binance USD-M Derivatives Pagination

`fetch_binance_derivatives_context_pages()` coordinates bounded multi-page
fetches for one Binance derivatives context family and symbol. Historical
time-range endpoints require explicit `start_time_ms` and `end_time_ms`.
Current open interest remains a one-page current-context fetch without
time-range params.

The paginator builds endpoint-specific requests through
`build_binance_derivatives_context_request()`, fetches each page through
`fetch_binance_derivatives_context_request()`, stores page URLs and fetch-result
IDs, and advances cursors from normalized timestamps. Kline and other
bucketed-period rows advance by bucket seconds; funding rows advance by source
timestamp plus one millisecond. Max-page exhaustion, blocked pages,
non-advancing cursors, missing bounded windows, and request-construction
failures are blocker metadata.

Pagination results do not write archive data, create coverage reports, run
workers, or relabel Binance context as Hyperliquid-native evidence.

## Binance USD-M Derivatives Archive Ingest

`ingest_binance_derivatives_context_pages_to_archive()` consumes a completed
`BinanceDerivativesContextPageResult` and writes local archive artifacts:

- raw JSONL.zst records under `datatype=derivatives_context`;
- generic silver Parquet rows under `dataset=derivatives_context`.

The ingest helper refuses blocked page results, empty page results, and rows
without source timestamps before writing files. Silver rows keep source
timestamps, publication timestamps, interval/period bucket metadata, dynamic
numeric fields, unit fields, raw fields, page-result refs, page fetch refs, raw
file refs, and the full research-only boundary flags. Dynamic field maps are
stored as deterministic JSON text so later family-specific schemas can be
derived without losing source provenance.

Archive ingest does not create accepted research coverage, candidate evidence,
worker scheduling, paper/live behavior, or Hyperliquid-native evidence.

## Binance USD-M Derivatives Coverage

`build_binance_derivatives_context_coverage_report()` consumes a
`BinanceDerivativesContextPageResult` plus its matching archive-ingest result
and returns a `DataFamilyCoverageReport` for the specific derivatives context
family. These reports are separate from Binance Vision candle/trade coverage
and keep `external_comparison` labels with
`binance_usdm_public_derivatives_context` as the source ID.

Coverage acceptance requires completed page and archive ingest evidence,
raw/silver archive refs, an archive snapshot ref, complete expected buckets,
and no blocker reasons. Current open-interest snapshot rows are reported but
blocked as `current_context_snapshot_only` because they are not historical
coverage windows. Missing buckets, missing archive refs, blocked page results,
blocked ingest results, missing row timestamps, missing bucket seconds, and
missing archive snapshots remain explicit non-accepted coverage reasons.

## Binance USD-M Derivatives Backfill Orchestration

`run_binance_derivatives_context_backfill()` is the bounded local orchestration
unit for one derivatives context family and symbol. It composes pagination,
archive ingest, and coverage report construction, then writes the coverage JSON
under `manifests/coverage_reports/`.

`BinanceDerivativesContextBackfillResult` records the page result ID, archive
ingest ID, coverage report ID/ref, accepted flag, blocker reasons, and full
research-only boundary flags. Completed status requires accepted coverage and
zero blockers; missing buckets, current-OI snapshot-only coverage, blocked
inputs, missing archive evidence, and other coverage blockers return blocked
status while still preserving the coverage JSON ref.

This orchestration helper is not a durable worker, scheduler, backtest input,
candidate signal, or promotion path.

## Binance USD-M Derivatives Worker Routing

The durable `binance_derivatives_context_backfill` worker kind is the
operational handoff for the single-family local derivatives context chain. It
requires one family, symbol, instrument ID, archive root, universe snapshot ref,
source registry ref, and symbol map ref, then delegates to
`run_binance_derivatives_context_backfill()`.

Worker specs may declare `source=fixture_payloads` for offline deterministic
payload replay or `source=public_api` for explicit public REST mode. Worker
outputs must surface the source mode, page result ID, archive ingest ID,
coverage report ID/ref, accepted flag, and blocker reasons. Completed and
blocked coverage outcomes are research evidence; invalid specs and preflight
failures are worker failures.

The worker route is still bounded to one family/symbol attempt. It does not
schedule broad backfills, create Hyperliquid-native evidence, or create
candidate, paper, live, order, sizing, runtime, or promotion readiness.

## Binance Vision ZIP Parser Validation

`parse_binance_vision_zip_bytes()` implements the first `DATA-005` parser
slice for local bytes only. It accepts one Binance Vision daily ZIP payload and
an optional checksum payload, verifies the checksum when supplied, requires
exactly one CSV member, and parses headered or Binance Vision headerless rows
for:

- trades;
- aggTrades;
- 1m klines.

`BinanceVisionParseResult` reports the ZIP SHA-256, checksum verification
state, archive CSV member name, row count, duplicate ID count, duplicate IDs,
kline gap count, input timestamp monotonicity, interval alignment status,
stable normalized-row hash, warnings, and full research-only boundary flags.

This parser does not fetch URLs, write raw/bronze/silver archive files, create
coverage reports, or mark data accepted. Download/cache, archive writes,
reconstructed-bar comparisons, and coverage reports are separate gates that
consume parser output.

## Binance Vision Local Archive Ingest

`ingest_binance_vision_zip_bytes_to_archive()` consumes local ZIP bytes through
the parser and writes archive artifacts without performing any network fetch.
For 1m klines it writes:

- raw parsed Binance Vision kline records;
- bronze candle Parquet rows;
- silver 1m bar Parquet rows.

For trades and aggTrades it writes raw microstructure trade captures through
the existing v2 microstructure archive path, plus quality and storage refs.

`BinanceVisionArchiveIngestResult` preserves parser diagnostics such as
checksum verification, duplicate count, kline gap count, monotonicity, and
interval alignment. These ingest outputs remain `accepted_research_evidence:
false` and `native_to_hyperliquid: false`. Download/cache, reconstructed-bar
comparison, and final coverage acceptance remain separate gates.

## Generic Trade-Bar Reconstruction

`reconstruct_trade_bars_from_rows()` starts the `DATA-014` venue-neutral
reconstruction foundation. It consumes already-normalized trade-like rows,
requires source registry and symbol-map refs, buckets rows by timestamp, and
emits deterministic `ReconstructedTradeBarRow` OHLCV records plus a
`TradeBarReconstructionReport`.

The helper keeps Hyperliquid-native and external-comparison rows separate.
Native rows may produce `native_hyperliquid` reconstruction labels, but remain
`accepted_historical_coverage_proof=false` until later coverage audits accept
separate evidence. External rows produce `external_comparison` labels and must
not be relabeled as Hyperliquid trades, fills, orders, or execution truth.

Empty inputs become blocker reports. Mixed native/external rows, mixed venues,
mixed symbols, bad expected windows, and input rows claiming accepted
historical coverage proof fail closed. This foundation does not write archive
rows, build gold panels, or create accepted coverage.

`compare_reconstructed_trade_bars_to_source_bars()` compares a generic
`TradeBarReconstructionReport` to source-native candle bars for the same venue,
symbol, market type, bucket size, and native/external provenance class. The
comparison records absolute OHLCV differences, pass/fail/missing/extra bucket
status, tolerance metadata, source registry and symbol-map refs, stable row
hashes, and a stable comparison report ID.

Missing reconstructed buckets, extra reconstructed buckets, tolerance breaches,
or mismatched venue/symbol/provenance become blocker evidence. Passing
comparison reports are quality metadata only; they do not create accepted
historical coverage proof or replace later data-family coverage gates.

## Orderflow Feature Reconstruction

`reconstruct_orderflow_features_from_trades()` starts the `DATA-015`
`reconstruct_vwap_and_flow_features` foundation. It consumes
already-normalized `TradeBarInputRow` records, requires source registry and
symbol-map refs, buckets rows by timestamp, and emits deterministic
`OrderflowFeatureRow` records with VWAP, buy/sell/unknown volumes,
buy/sell/unknown quote volumes, trade counts, source row hashes, and volume
imbalance features. `OrderflowFeatureReport` records row counts, source refs,
stable hashes, missing-side counts, and blocker metadata.

Native Hyperliquid rows and external-comparison rows remain separated. Native
feature rows may carry `native_hyperliquid`; external rows carry
`external_comparison`. Empty inputs, missing trade-side information, mixed
native/external provenance, mixed venues/symbols/coins/market types, and
zero-volume buckets fail closed or become explicit blocker metadata. These
features are research-only candidates for later gold panels; they do not write
archive rows, create gold panel rows, or create accepted historical coverage
proof.

## Funding/OI Context Feature Reconstruction

`reconstruct_funding_oi_features_from_context_rows()` continues the `DATA-015`
feature foundation for `reconstruct_funding_oi_features`. It consumes
already-normalized derivatives context rows, including the existing Binance
USD-M `BinanceDerivativesContextNormalizedRow` shape, and emits deterministic
`DerivativesContextFeatureRow` records for funding rate history, open
interest, open-interest statistics, and basis context. Rows preserve source
IDs, source registry refs, symbol-map refs, family names, timestamps,
interval/period metadata, numeric features, units, source row hashes, and
native/external provenance.

The helper keeps native Hyperliquid and external-comparison context separated.
Empty input, unsupported families, missing timestamps, missing numeric fields,
non-finite numeric values, mixed native/external provenance, and mixed venue or
symbol provenance fail closed or become explicit blocker metadata. These
features are research-only candidates for later gold panels; they do not write
archive rows, create gold panel rows, or create accepted historical coverage
proof.

## BBO Spread Feature Reconstruction

`reconstruct_bbo_spread_features_from_rows()` continues the `DATA-015`
feature foundation for `reconstruct_bbo_spread_features`. It consumes
already-normalized best-bid/offer event rows, including archive `BBOEventRow`
compatible payloads, and emits deterministic `BBOFeatureRow` records with mid
price, absolute spread, spread bps, and top-of-book size imbalance. Reports
preserve source IDs, source registry refs, symbol-map refs, timestamp/sequence
metadata, source row hashes, and native/external provenance.

The helper keeps native Hyperliquid and external-comparison BBO rows separated.
Empty input, missing timestamps, missing top-of-book sizes, crossed books,
non-positive prices, mixed native/external provenance, and mixed venue or
symbol provenance fail closed or become explicit blocker metadata. These
features are research-only candidates for later gold panels; they do not write
archive rows, create gold panel rows, or create accepted historical coverage
proof.

## L2 Depth Feature Reconstruction

`reconstruct_l2_depth_features_from_rows()` continues the `DATA-015` feature
foundation for `reconstruct_l2_depth_features`. It consumes already-normalized
L2 snapshot rows, including archive `L2BookSnapshotRow` compatible payloads,
and emits deterministic `L2DepthFeatureRow` records with bid depth, ask depth,
total depth, depth imbalance, and optional book-level metadata. Reports
preserve source IDs, source registry refs, symbol-map refs, timestamp/sequence
metadata, source row hashes, and native/external provenance.

The helper keeps native Hyperliquid and external-comparison L2 rows separated.
Empty input, missing timestamps, zero total depth, negative depths, invalid
book levels, mixed native/external provenance, and mixed venue or symbol
provenance fail closed or become explicit blocker metadata. These features are
research-only candidates for later gold panels; they do not write archive rows,
create gold panel rows, or create accepted historical coverage proof.

## Cross-Venue Basis Feature Reconstruction

`reconstruct_cross_venue_basis_features_from_prices()` completes the `DATA-015`
feature foundation for `reconstruct_cross_venue_basis_features`. It consumes
already-normalized price observation rows, requires a requested primary venue,
and emits deterministic `CrossVenueBasisFeatureRow` records with absolute and
bps price differences between the primary venue and each comparison venue.
Reports preserve source IDs, venue symbols, source registry refs, symbol-map
refs, timestamp metadata, source row hashes, and explicit primary/comparison
native flags.

Cross-venue rows are always `external_comparison` and never
Hyperliquid-native evidence. Empty input, insufficient venue coverage, missing
timestamps, missing or duplicate primary venue prices, missing comparison
prices, mixed coin/market/price-kind context, and non-positive prices fail
closed or become explicit blocker metadata. These features are research-only
candidates for later gold panels; they do not write archive rows, create gold
panel rows, or create accepted historical coverage proof.

## Binance Vision Reconstructed-Bar Comparison

`compare_binance_vision_reconstructed_bars()` reconstructs 1m OHLCV buckets
from parsed trades or aggTrades and compares those buckets against parsed 1m
klines. `BinanceVisionBarComparisonReport` records source and kline row hashes,
tolerances, per-bucket OHLCV differences, missing reconstructed buckets, pass
counts, failure counts, and blocker reasons.

Passing reports are quality metadata only. They are not accepted coverage
evidence by themselves and do not replace later data-family coverage reports.

## Binance Vision Data-Family Coverage Reports

`build_binance_vision_data_family_coverage_report()` turns one Binance Vision
availability row plus optional parser, ingest, and reconstructed-bar comparison
evidence into a deterministic `DataFamilyCoverageReport`.

Daily trade and aggTrade reports use a one-day presence bucket. Daily 1m kline
reports use 1,440 one-minute buckets. Missing ZIPs, blocked mappings, missing
parser output, missing archive ingest, missing archive snapshots, checksum
verification gaps when checksums were available, duplicate IDs, kline gaps,
interval misalignment, incomplete 1m coverage, and failed reconstructed-bar
comparison become explicit blocker reasons.

Accepted reports are labeled `external_comparison`. They may support
cross-venue research reporting, but they remain `native_to_hyperliquid=false`
by source semantics and must not be used as Hyperliquid-native fills, orders,
or execution truth.

## Symbol Map Rules

`VenueSymbolMapRow` maps one Hyperliquid coin to per-venue symbols and mapping
states. It must preserve:

- Hyperliquid coin spelling as received from the venue;
- as-of date;
- canonical base asset;
- per-venue `market_type`;
- per-venue mapping status: `verified`, `missing`, `ambiguous`, `delisted`,
  `not_checked`, or `manual_review_required`;
- provenance refs.

`require_verified_external_mapping()` must be used before a downstream external
backfill runs for a venue/symbol pair. Missing, ambiguous, delisted,
not-checked, or manual-review mappings are blocker evidence, not hidden skips.

The resolver may generate deterministic candidate symbols for Binance, Bybit,
OKX, Bitget, MEXC, Gate, KuCoin, HTX, dYdX, Deribit, Coinbase, Kraken, Pyth,
DefiLlama, DexScreener, and GeckoTerminal. Candidate generation is not
verification.
Only explicit `SymbolProbeResult(status="verified", ...)` evidence can mark a
mapping verified. Probe results with `ambiguous` or
`manual_review_required` status must include notes and become blocker reasons
on the emitted `VenueSymbolMapRow`.

## Forbidden

- A paid/keyed source must not be accepted by a strict-zero-dollar registry.
- A requester-pays source must not be marked strict-zero-dollar allowed.
- A free sample must not be treated as historical coverage proof.
- A spot symbol must not be used as a perpetual mapping.
- External venue rows must not be relabeled as Hyperliquid-native fills,
  trades, or execution truth.
- Registry or symbol-map artifacts must not emit paper/live/order/sizing,
  runtime-mode, candidate-pack, or promotion claims.
