# WPR106-541 - V2 Central Market History March Time Depth

Status: completed
Owner: Codex Research Agent
Date: 2026-06-25

## Objective

Continue the centralized market-history collection toward the active
research-only, data-first, multi-instrument v2 scope by adding March 2024
official no-paid trade and orderflow-style market-history archives into
`data/research/central_market_history/**` without exceeding the 150 GiB local
cap.

Hyperliquid remains preferred where usable, but the central market-history
data-readiness lane must not fail solely because Hyperliquid historical
coverage is absent for a symbol/window when eligible no-paid Binance, Bybit, or
other repo-supported provider data is present, valid, and manifested. This
packet does not alter stricter Hyperliquid-native autonomous readiness gates.

This packet does not create candidate-pack, paper/live, order, sizing,
runtime-mode, promotion, autonomous strategy, or production trading readiness.

## Starting State

At packet start the central store contains 2875 files and 23806088296 bytes
(approximately 22.171 GiB), leaving approximately 127.829 GiB under the 150 GiB
cap. The append manifest has 46 prior rows from WPR106-534 through WPR106-540.

The current worktree also contains prior uncommitted WPR106-527 through
WPR106-540 changes. They are treated as authoritative and must not be reverted
or rewritten outside this packet's scope.

## Allowed Paths

- `docs/work_packets/WPR106-541-v2-central-market-history-march-time-depth.md`
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
  through WPR106-540.
- Collect public official Binance USD-M aggregate-trade ZIPs and Bybit public
  linear trading GZIPs for March 2024 BTC, ETH, SOL, BNB, XRP, and DOGE where
  reachable.
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

WPR106-541 kept all accepted generated artifacts under
`data/research/central_market_history/**`. Final measured central root size is
26858531485 bytes, approximately 25.014 GiB, leaving approximately 124.986 GiB
under the 150 GiB cap. The append manifest now has 54 rows.

WPR106-541 appended 660,000 normalized rows through eight additional central
batches:

- `wpr106-541-btc-mar2024-early-trade-orderflow`: 40,000 BTC rows from
  March 1-4, 2024 official Binance USD-M aggregate-trade ZIPs and Bybit
  public trading GZIPs. The initial broader BTC/SOL/ETH pass exceeded the
  bounded shell timeout; an interrupted BTC March 5 Binance ZIP was validated
  as incomplete and removed before any cache reuse or manifest acceptance.
- `wpr106-541-bnb-mar2024-partial-trade-orderflow`: 195,000 BNB rows from
  March 1-20, 2024 Binance USD-M aggregate-trade ZIPs and March 1-19, 2024
  Bybit public trading GZIPs. An interrupted Bybit March 20 GZIP was validated
  as incomplete and removed.
- `wpr106-541-bnb-mar2024-continuation-trade-orderflow`: 115,000 BNB rows
  from the remaining March 20-31, 2024 Bybit public trading and March 21-31,
  2024 Binance USD-M aggregate-trade archives. This completed the intended BNB
  March provider slice after the partial-batch deferrals.
- `wpr106-541-xrp-mar2024-week1-trade-orderflow`: 70,000 XRP rows from
  March 1-7, 2024 Binance USD-M aggregate-trade and Bybit public trading
  archives.
- `wpr106-541-xrp-mar2024-week2-trade-orderflow`: 70,000 XRP rows from
  March 8-14, 2024 Binance USD-M aggregate-trade and Bybit public trading
  archives.
- `wpr106-541-xrp-mar2024-week3-trade-orderflow`: 70,000 XRP rows from
  March 15-21, 2024 Binance USD-M aggregate-trade and Bybit public trading
  archives.
- `wpr106-541-xrp-mar2024-week4-trade-orderflow`: 70,000 XRP rows from
  March 22-28, 2024 Binance USD-M aggregate-trade and Bybit public trading
  archives.
- `wpr106-541-xrp-mar2024-tail-trade-orderflow`: 30,000 XRP rows from
  March 29-31, 2024 Binance USD-M aggregate-trade and Bybit public trading
  archives.

Across accepted WPR106-541 batches, 132 official no-paid archives completed:
66 Binance USD-M daily aggregate-trade ZIPs and 66 Bybit public trading GZIPs.
All accepted rows have source metadata, raw checksums, normalized Parquet,
raw JSONL, quality reports, source-discovery reports, and append-only manifest
entries. The eight accepted WPR106-541 batches reported zero duplicate rows.

The aggregate normalized central Parquet set now contains 7,993,343 rows:

- Providers: `binance_usdm=5380980`, `bybit_linear=1926913`,
  `binance_spot=352384`, `bybit_inverse=178560`, `hyperliquid=144506`,
  `bybit_spot=10000`.
- Families: `orderflow=5135999`, `ohlcv=1412324`, `trade=1266000`,
  `metadata=179020`.
- Timeframes: event/metadata rows without a row timeframe at `6581019`,
  `1h=1251630`, `15m=116927`, and `1d=43767`.
- Top symbols: `BTC=866521`, `ETH=831581`, `BNB=814091`, `XRP=814090`,
  `DOGE=504091`, and `SOL=504091`.

WPR106-541 also writes
`wpr106-541-remaining-march-source-deferrals-source_discovery_report-d9f297025e08.json`
for the March sources left to a next bounded packet: BTC March 5-31 and full
ETH, SOL, and DOGE March 2024 Binance USD-M/Bybit public trading source URLs.
Those `deferred_next_packet` records are exact continuation targets, not
central-readiness failures. BTC/ETH/SOL/DOGE remain fixture, smoke-test,
reference, and legacy evidence symbols; they are not the full v2 product
scope.

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
the touched central data-source lane returned no matches. A final raw-integrity
pass checked all 132 WPR106-541 raw source archives, covering 1,890,438,230
bytes, and found no invalid ZIP or GZIP files. No `.part` files or active
WPR106-541 collection processes remained after collection; only unrelated local
HTTP server Python processes were present.
