# Data Contract

Every normalized research dataset must have a manifest.

## Required manifest fields

```json
{
  "manifest_version": "data-manifest-v1",
  "research_only": true,
  "source_name": "binance_vision | binance_rest | bybit_archive | crypto_lake | hyperliquid_archive",
  "source_type": "archive | rest | websocket_capture | local_file",
  "symbol": "BTCUSDT",
  "data_family": "kline | trade | agg_trade | book_ticker | depth_snapshot | funding_rate | open_interest | premium_index | liquidation | user_fill | order_event | position_snapshot",
  "event_time_field": "event_time_ms",
  "receive_time_field": "receive_time_ms",
  "receive_time_unavailable_reason": null,
  "start_time_ms": 0,
  "end_time_ms": 0,
  "row_count": 0,
  "schema_version": "family-schema-v1",
  "content_hash": "sha256",
  "normalized_fields": [],
  "missing_fields": [],
  "quality_flags": [],
  "non_promotable_reasons": []
}
```

## Rules

- Event time is mandatory.
- Receive time is preferred. If unavailable, the manifest must explain why and the dataset is non-promotable for live-like latency claims.
- Missing context must be explicit missingness, not silent zero-fill.
- Provider-specific field names must be normalized into canonical fields.
- Data-quality reports must include gaps, duplicates, stale receive times, source mismatches, zero-row manifests, and non-promotable sources.

## R106 Historical Data Catalog

`historical_data_catalog.json` is the required operator source of truth for
current BTCUSDT/ETHUSDT research historical data. It records:

- active fixture/readiness/cycle/discovery paths selected for required runs
- provider states for Binance Vision, Crypto Lake, Bybit archive, and
  Hyperliquid archive
- candidate-depth status separately from fixture integrity
- source priority and merge policy

The catalog is still research-only, observe-only, and `promotion_ready: false`.
Registered providers must not become active catalog sources until downloader,
parser, gap/duplicate/hash validation, and missingness contracts exist.
