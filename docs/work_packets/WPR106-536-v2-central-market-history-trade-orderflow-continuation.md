# WPR106-536 - V2 Central Market History Trade Orderflow Continuation

Status: completed
Owner: Codex Research Agent
Date: 2026-06-25

## Objective

Continue the WPR106-534/WPR106-535 centralized market-history store by
collecting additional official no-paid trade and orderflow-style market-history
archives into `data/research/central_market_history/**` without exceeding the
150 GiB local cap. This packet prioritizes BTC/ETH January 2024 public
Binance and Bybit trade/orderflow archives because they are high-value,
comparable, provider-provenanced, and bounded enough for reliable incremental
collection.

Hyperliquid remains preferred where usable, but the central market-history
data-readiness lane must not fail solely because Hyperliquid historical
coverage is absent for a symbol/window when eligible no-paid Binance, Bybit, or
other repo-supported provider data is present, valid, and manifested. This
packet does not alter stricter Hyperliquid-native autonomous readiness gates.

This packet does not create candidate-pack, paper/live, order, sizing,
runtime-mode, promotion, autonomous strategy, or production trading readiness.

## Starting State

At packet start the central store contains 1345 files and 3438069889 bytes
(approximately 3.202 GiB), leaving approximately 146.798 GiB under the 150 GiB
cap. The append manifest has seven prior rows from WPR106-534 and WPR106-535.

The current worktree also contains prior uncommitted WPR106-527 through
WPR106-535 changes. They are treated as authoritative and must not be reverted
or rewritten outside this packet's scope.

## Allowed Paths

- `docs/work_packets/WPR106-536-v2-central-market-history-trade-orderflow-continuation.md`
- `docs/PRODUCT_SCOPE.md`
- `docs/contracts/autonomous_readiness_contract.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/v2/data_sources/central_market_history.py`
- `src/tradingbotsuite/v2/data_sources/central_market_history_collection.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `tests/v2/test_central_market_history_store_phase76.py`
- `tests/v2/test_central_market_history_collection_phase77.py`
- New generated central market-history artifacts under
  `data/research/central_market_history/**`

## No-Touch Paths

- Live runtime, order-placement, broker/execution, sizing, runtime config,
  promotion, shadow, and candidate-pack truth-layer paths.
- Existing generated research evidence under `data/research/**`, except the
  append-only `data/research/central_market_history/**` output root.
- Secrets, `.env`, credential files, private caches, local SQLite operator
  databases, requester-pays data, paid sources, fixture-only/synthetic data as
  accepted evidence, sandbox-only evidence as accepted evidence, supplied-ref
  evidence without verifiable provenance, and generated `outputs/**`.

## Boundary

All new artifacts and models preserve:

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

## Plan

- Reuse the WPR106-535 central collection helpers and budget checks.
- Collect additional public official Binance USD-M aggregate-trade ZIPs and
  Bybit public derivatives trading GZIPs in small BTC/ETH January 2024 chunks.
- Preserve raw compressed source files where practical, normalize bounded
  sample rows per file into append-only Parquet/manifest batches, and record
  source discovery reports, checksums, coverage, quality, and exact blockers.
- Treat trade/orderflow families with relaxed cross-provider equality:
  provenance, schema validity, timestamp sanity, monotonicity, nonempty rows,
  and coverage metrics are required; strict row equality is not.
- Stop or downshift collection before any pass risks the 150 GiB cap or
  unreliable local runtime behavior.
- Update control docs only if this packet discovers a new blocker or changes
  the central data-readiness contract.

## Expected Validation

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_central_market_history_store_phase76.py tests/v2/test_central_market_history_collection_phase77.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest focused data/provider/storage/manifest tests -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2 -q
git diff --check
rg boundary scans for forbidden live/order/sizing/runtime/promotion/candidate-pack drift
```

## Results

Implemented two collection-helper extensions:

- `build_bybit_index_plan()` plus `rows_from_bybit_index_gzip()` for public
  Bybit `premium_index` and `spot_index` daily archives. These files are stored
  as metadata/event rows because they carry minute OHLC index values but no
  trade volume.
- `build_bybit_spot_monthly_trades_plan()` for public Bybit spot monthly trade
  archives.

WPR106-536 kept all generated accepted artifacts under
`data/research/central_market_history/**`. Final measured central root size is
9039839008 bytes, approximately 8.419 GiB, leaving approximately 141.581 GiB
under the 150 GiB cap. The append manifest now has 18 rows.

WPR106-536 appended 1,033,560 normalized rows through 11 additional central
batches:

- `wpr106-536-btc-jan09-trade-orderflow-cache`: 10,000 BTC rows from two
  validated January 9 raw files. The original Jan 9-15 `httpx` pass timed out;
  one partial invalid Jan 10 ZIP was removed, and unattempted files were
  recorded as source blockers in the discovery report.
- `wpr106-536-btc-jan10-trade-orderflow`: 10,000 BTC rows from Binance USD-M
  and Bybit linear January 10 trade/orderflow archives.
- `wpr106-536-btc-jan11-jan15-trade-orderflow`: 50,000 BTC rows.
- `wpr106-536-btc-jan16-jan23-trade-orderflow`: 80,000 BTC rows.
- `wpr106-536-btc-jan24-jan31-trade-orderflow`: 80,000 BTC rows.
- `wpr106-536-eth-jan01-jan10-trade-orderflow`: 100,000 ETH rows.
- `wpr106-536-eth-jan11-jan20-trade-orderflow`: 100,000 ETH rows.
- `wpr106-536-eth-jan21-jan31-trade-orderflow`: 110,000 ETH rows.
- `wpr106-536-bybit-index-btc-eth-jan2024`: 178,560 BTC/ETH Bybit inverse
  premium-index and spot-index metadata rows from 124 daily public archives.
- `wpr106-536-binance-spot-btc-eth-jan2024-aggtrades`: 310,000 Binance spot
  BTC/ETH aggregate-trade rows from 62 daily public archives.
- `wpr106-536-bybit-spot-eth-jan2024`: 5,000 Bybit spot ETH trade rows from
  the January 2024 public monthly archive. The raw gzip was fully read after a
  transient `curl` slow-transfer retry message and passed integrity reading.

The aggregate normalized central Parquet set now contains 2,523,343 rows:

- Providers: `bybit_linear=976913`, `binance_usdm=860980`,
  `binance_spot=352384`, `bybit_inverse=178560`, `hyperliquid=144506`,
  `bybit_spot=10000`.
- Families: `ohlcv=1412324`, `orderflow=615999`, `trade=316000`,
  `metadata=179020`.
- Timeframes: `1h=1251630`, `15m=116927`, `1d=43767`, and
  event/metadata rows without a row timeframe at `1111019`.

The previous strict Hyperliquid-only interpretation remains out of the central
market-history data-readiness path. Hyperliquid remains preferred when usable,
but central multi-provider data readiness must not fail solely because
Hyperliquid history is missing for a symbol/window when valid no-paid provider
data is present. This packet does not close `ISSUE-R106-032` and does not
create Hyperliquid-native autonomous strategy readiness, candidate-pack
evidence, paper/live signals, order placement, sizing instructions,
runtime-mode changes, promotion behavior, or production trading readiness.

Validation passed during this packet:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_central_market_history_store_phase76.py tests/v2/test_central_market_history_collection_phase77.py -q
# 11 passed, 1 StarletteDeprecationWarning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_central_market_history_store_phase76.py tests/v2/test_central_market_history_collection_phase77.py tests/v2/test_data_source_registry_phase37.py tests/v2/test_symbol_map_resolver_phase38.py tests/v2/test_universe_data_source_manifest_bridge_phase39.py tests/v2/test_historical_dataset_collection_phase36.py tests/v2/test_bybit_okx_availability_phase55.py tests/v2/test_bybit_okx_fetch_normalize_phase56.py tests/v2/test_binance_vision_availability_phase40.py tests/v2/test_binance_vision_parser_phase41.py tests/v2/test_binance_vision_archive_ingest_phase42.py tests/v2/test_binance_vision_coverage_phase44.py tests/v2/test_binance_vision_downloader_phase45.py tests/v2/test_binance_vision_backfill_phase46.py tests/v2/test_binance_vision_backfill_batch_phase47.py tests/v2/test_binance_derivatives_context_phase48.py tests/v2/test_binance_derivatives_fetch_phase49.py tests/v2/test_binance_derivatives_pagination_phase50.py tests/v2/test_binance_derivatives_archive_ingest_phase51.py tests/v2/test_binance_derivatives_coverage_phase52.py tests/v2/test_binance_derivatives_backfill_phase53.py tests/v2/test_binance_derivatives_worker_phase54.py tests/v2/test_data_quality_phase6.py tests/v2/test_data_family_coverage_gate_phase69.py tests/v2/archive/test_archive_phase4.py tests/v2/archive/test_archive_phase8.py -q
# 136 passed, 1 StarletteDeprecationWarning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts -q
# 463 passed, 1 StarletteDeprecationWarning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2 -q
# 563 passed, 1 StarletteDeprecationWarning
git diff --check
# exit 0 with existing LF-to-CRLF working-copy warnings
```

Targeted boundary scans for forbidden true flags, live/runtime/promotion/order
imports, and paper/live/order/sizing/signal/candidate-pack readiness drift in
the touched central data-source lane returned no matches.
