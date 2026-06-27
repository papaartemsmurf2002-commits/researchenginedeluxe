# WPR106-540 - V2 Central Market History February Alt Extension

Status: completed
Owner: Codex Research Agent
Date: 2026-06-25

## Objective

Continue the centralized market-history collection toward the active
research-only, data-first, multi-instrument v2 scope by adding February 2024
official no-paid trade and orderflow-style market-history archives into
`data/research/central_market_history/**` without exceeding the 150 GiB local
cap. This packet extends February time depth for non-reference instruments that
already have January 2024 central-store coverage.

Hyperliquid remains preferred where usable, but the central market-history
data-readiness lane must not fail solely because Hyperliquid historical
coverage is absent for a symbol/window when eligible no-paid Binance, Bybit, or
other repo-supported provider data is present, valid, and manifested. This
packet does not alter stricter Hyperliquid-native autonomous readiness gates.

This packet does not create candidate-pack, paper/live, order, sizing,
runtime-mode, promotion, autonomous strategy, or production trading readiness.

## Starting State

At packet start the central store contains 2551 files and 20818994790 bytes
(approximately 19.389 GiB), leaving approximately 130.611 GiB under the 150 GiB
cap. The append manifest has 37 prior rows from WPR106-534 through WPR106-539.

The current worktree also contains prior uncommitted WPR106-527 through
WPR106-539 changes. They are treated as authoritative and must not be reverted
or rewritten outside this packet's scope.

## Allowed Paths

- `docs/work_packets/WPR106-540-v2-central-market-history-february-alt-extension.md`
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

- Reuse the central collection helpers and budget checks from WPR106-535
  through WPR106-539.
- Collect public official Binance USD-M aggregate-trade ZIPs and Bybit public
  linear trading GZIPs for February 2024 ADA, AVAX, LINK, SUI, LTC, DOT, TRX,
  UNI, and FIL where reachable.
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

WPR106-540 kept all accepted generated artifacts under
`data/research/central_market_history/**`. Final measured central root size is
23806088296 bytes, approximately 22.171 GiB, leaving approximately 127.829 GiB
under the 150 GiB cap. The append manifest now has 46 rows.

WPR106-540 appended 1,305,000 normalized rows through nine additional central
batches:

- `wpr106-540-ada-feb2024-trade-orderflow`: 145,000 ADA rows from 29 Binance
  USD-M aggregate-trade ZIPs; 29 Bybit public trading paths returned 404 and
  are recorded as provider-specific source blockers.
- `wpr106-540-avax-feb2024-trade-orderflow`: 145,000 AVAX rows from 29
  Binance USD-M aggregate-trade ZIPs; 29 Bybit public trading paths returned
  404 and are recorded as provider-specific source blockers.
- `wpr106-540-link-feb2024-trade-orderflow`: 145,000 LINK rows from 29 Binance
  USD-M aggregate-trade ZIPs; 29 Bybit public trading paths returned 404 and
  are recorded as provider-specific source blockers.
- `wpr106-540-sui-feb2024-trade-orderflow`: 145,000 SUI rows from 29 Binance
  USD-M aggregate-trade ZIPs; 29 Bybit public trading paths returned 404 and
  are recorded as provider-specific source blockers.
- `wpr106-540-ltc-feb2024-trade-orderflow`: 145,000 LTC rows from 29 Binance
  USD-M aggregate-trade ZIPs; 29 Bybit public trading paths returned 404 and
  are recorded as provider-specific source blockers.
- `wpr106-540-dot-feb2024-trade-orderflow`: 145,000 DOT rows from 29 Binance
  USD-M aggregate-trade ZIPs; 29 Bybit public trading paths returned 404 and
  are recorded as provider-specific source blockers.
- `wpr106-540-trx-feb2024-trade-orderflow`: 145,000 TRX rows from 29 Binance
  USD-M aggregate-trade ZIPs; 29 Bybit public trading paths returned 404 and
  are recorded as provider-specific source blockers.
- `wpr106-540-uni-feb2024-trade-orderflow`: 145,000 UNI rows from 29 Binance
  USD-M aggregate-trade ZIPs; 29 Bybit public trading paths returned 404 and
  are recorded as provider-specific source blockers.
- `wpr106-540-fil-feb2024-trade-orderflow`: 145,000 FIL rows from 29 Binance
  USD-M aggregate-trade ZIPs; 29 Bybit public trading paths returned 404 and
  are recorded as provider-specific source blockers.

All 261 Binance USD-M official public archives downloaded, parsed, and
manifested. The 261 Bybit public trading source probes for these symbols and
dates returned official-path 404 responses, so no Bybit rows were accepted for
this packet. Those blockers do not fail central market-history readiness
because comparable no-paid Binance data is present, valid, and manifested with
source provenance. Raw compressed files were preserved, checksummed, and
referenced from source metadata and source-discovery reports.

The aggregate normalized central Parquet set now contains 7,333,343 rows:

- Providers: `binance_usdm=5050980`, `bybit_linear=1596913`,
  `binance_spot=352384`, `bybit_inverse=178560`, `hyperliquid=144506`,
  `bybit_spot=10000`.
- Families: `orderflow=4805999`, `ohlcv=1412324`, `trade=936000`,
  `metadata=179020`.
- Timeframes: event/metadata rows without a row timeframe at `5921019`,
  `1h=1251630`, `15m=116927`, and `1d=43767`.

This packet extends February 2024 time depth for non-reference instruments
already represented in the central store. BTC and ETH remain fixture/reference
symbols, not the full v2 product scope.

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
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_central_market_history_store_phase76.py tests\v2\test_central_market_history_collection_phase77.py -q
# 11 passed, 1 StarletteDeprecationWarning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_central_market_history_store_phase76.py tests/v2/test_central_market_history_collection_phase77.py tests/v2/test_data_source_registry_phase37.py tests/v2/test_symbol_map_resolver_phase38.py tests/v2/test_universe_data_source_manifest_bridge_phase39.py tests/v2/test_historical_dataset_collection_phase36.py tests/v2/test_bybit_okx_availability_phase55.py tests/v2/test_bybit_okx_fetch_normalize_phase56.py tests/v2/test_binance_vision_availability_phase40.py tests/v2/test_binance_vision_parser_phase41.py tests/v2/test_binance_vision_archive_ingest_phase42.py tests/v2/test_binance_vision_coverage_phase44.py tests/v2/test_binance_vision_downloader_phase45.py tests/v2/test_binance_vision_backfill_phase46.py tests/v2/test_binance_vision_backfill_batch_phase47.py tests/v2/test_binance_derivatives_context_phase48.py tests/v2/test_binance_derivatives_fetch_phase49.py tests/v2/test_binance_derivatives_pagination_phase50.py tests/v2/test_binance_derivatives_archive_ingest_phase51.py tests/v2/test_binance_derivatives_coverage_phase52.py tests/v2/test_binance_derivatives_backfill_phase53.py tests/v2/test_binance_derivatives_worker_phase54.py tests/v2/test_data_quality_phase6.py tests/v2/test_data_family_coverage_gate_phase69.py tests/v2/archive/test_archive_phase4.py tests/v2/archive/test_archive_phase8.py -q
# 136 passed, 1 StarletteDeprecationWarning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
# 463 passed, 1 StarletteDeprecationWarning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2 -q
# 563 passed, 1 StarletteDeprecationWarning
git diff --check
# exit 0 with existing LF-to-CRLF working-copy warnings
```

Targeted boundary scans for forbidden true flags, live/runtime/promotion/order
imports, and paper/live/order/sizing/signal/candidate-pack readiness drift in
the touched central data-source lane returned no matches. No `.part` files or
active WPR106-540 collection processes remained after collection.
