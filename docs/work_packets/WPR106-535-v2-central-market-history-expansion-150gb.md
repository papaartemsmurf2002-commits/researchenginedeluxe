# WPR106-535 - V2 Central Market History Expansion 150GB Cap

Status: completed
Owner: Codex Research Agent
Date: 2026-06-25

## Objective

Continue WPR106-534 central market-history collection toward the full v2
research-only multi-provider data lane, with a hard local storage ceiling of
150 GiB for `data/research/central_market_history/**`. Collect additional
no-paid market-history data from eligible providers as far as practical under
that ceiling, preserve raw downloads where practical, normalize rows into the
central append-only store, and record exact source blockers for data that is
missing, too large for the current pass, unreachable, paid, requester-pays,
synthetic, fixture-only, sandbox-only, supplied-ref, or unverifiable.

This packet must make the prior strict Hyperliquid-only data-readiness
interpretation non-conflicting for future agents: Hyperliquid remains preferred
when usable, but central multi-provider market-history data readiness must not
fail solely because Hyperliquid historical coverage is missing for a
symbol/window when comparable no-paid Binance, Bybit, or other repo-supported
provider data is present and valid.

This packet does not create candidate-pack, paper/live, order, sizing,
runtime-mode, promotion, autonomous strategy, or production trading readiness.

## Starting State

WPR106-534 created the central store under
`data/research/central_market_history/**`. At packet start the root contains
20 files and approximately 0.466 GiB, leaving approximately 149.5 GiB of
headroom under the 150 GiB cap.

The current worktree also contains prior uncommitted WPR106-527 through
WPR106-534 changes. They are treated as authoritative and must not be reverted
or rewritten outside this packet's scope.

## Allowed Paths

- `docs/work_packets/WPR106-535-v2-central-market-history-expansion-150gb.md`
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

- Add or reuse a bounded collection planner that accounts for existing central
  store bytes before each download and refuses planned writes that would exceed
  150 GiB.
- Prioritize 2024-01-01 through the latest completed month available before
  2026-06-25 for v2-relevant symbols from the existing WPR106-533/WPR106-534
  universe and BTC/ETH reference symbols.
- Collect or reuse additional strict-free official public/archive data:
  Binance USD-M/spot candles and aggregate trades where size budget permits,
  Bybit public candles/trades/index archives where reachable, Hyperliquid
  public metadata/recent snapshots where available, and existing local central
  or repo-supported refs.
- Preserve compressed/raw source files where practical, write normalized
  Parquet/JSONL rows through the WPR106-534 central store, append manifests,
  and record checksums, coverage, quality, source discovery, source blockers,
  and budget accounting.
- Retain all valid provider rows when normalized OHLCV divergence exceeds five
  percent and mark provider-specific quality status. Treat trade/orderflow/book
  families with relaxed provenance/schema/timestamp/monotonicity/nonempty/
  coverage checks rather than strict cross-provider equality.
- Update control docs only as needed to make the multi-provider data-readiness
  contract explicit and non-conflicting for future agents.

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

Implemented `tradingbotsuite.v2.data_sources.central_market_history_collection`
and phase-77 focused tests. The collector helpers add local tree-size
accounting, a hard 150 GiB budget report, source plans for public Binance and
Bybit archives, parser support for Binance kline/aggTrade ZIPs, Bybit
derivatives/spot trade GZIPs, Bybit MT4 kline GZIPs, Bybit kline API JSON,
Hyperliquid candle JSON, and source-discovery reports with checksums and
canonical research-only boundary fields. The collection layer refuses planned
writes that would exceed the configured central root budget.

WPR106-535 kept all generated data under
`data/research/central_market_history/**`. Final measured central root size is
3438069889 bytes, approximately 3.202 GiB, leaving approximately 146.798 GiB
under the 150 GiB cap. The central append manifest now has seven rows: the
original WPR106-534 batch plus six WPR106-535 batch manifests.

WPR106-535 appended these normalized batches:

- `wpr106-535-binance-monthly-ohlcv-expansion`: 491281 normalized Binance
  1h OHLCV rows. The source-discovery report has 748 probes, 678 completed,
  and 70 exact 404 blockers for unavailable/newer Binance USD-M symbol-months.
- `wpr106-535-bybit-api-1h-ohlcv-expansion`: 441287 normalized Bybit linear
  1h OHLCV rows. The source-discovery report has 510 probes, 451 completed,
  and 59 empty-page blockers for unavailable/pre-listing symbol windows.
- `wpr106-535-hyperliquid-public-recent-expansion`: 144226 normalized
  Hyperliquid public recent 1h candle/metadata rows. The source-discovery
  report has 31 probes, 30 completed, and one exact Hyperliquid HTTP 500
  blocker for KPEPE `candleSnapshot`.
- `wpr106-535-btc-jan2-jan8-trade-orderflow-cache`: 70000 normalized BTC
  trade/orderflow rows from seven cached Binance aggTrade ZIPs and seven
  cached Bybit trading GZIPs. These complete raw files were left by a timed-out
  larger pass and were validated before manifesting; the timed-out Python
  process was stopped.
- `wpr106-535-bybit-mt4-15m-btc-eth-expansion-v2`: 116527 normalized Bybit
  MT4 15m BTC/ETH OHLCV rows after 38 in-batch duplicates were preserved in
  duplicate-group provenance. The corrected source-discovery report has 58
  probes, 46 completed, and 12 exact 404 blockers for BTC/ETH 2025-12 through
  2026-05 MT4 monthly files. This subset batch is intentionally
  `centralized_market_history_ready=false` because the 15m MT4 coverage is
  partial; it does not negate the overall central data-readiness batches.
- `wpr106-535-bybit-spot-btc-jan2024-expansion-v2`: 5000 normalized Bybit
  spot BTC January 2024 trade rows from the previously deferred 89235350-byte
  official public archive. The raw file is preserved and checksummed.

The aggregate normalized central Parquet set now contains 1489783 rows:

- Providers: `bybit_linear=706913`, `binance_usdm=590980`,
  `hyperliquid=144506`, `binance_spot=42384`, `bybit_spot=5000`.
- Families: `ohlcv=1412324`, `trade=41000`, `orderflow=35999`,
  `metadata=460`.
- Timeframes: `1h=1251630`, `15m=116927`, `1d=43767`, and
  event/metadata rows without a timeframe at `77459`.

Issues found and fixed:

- Binance spot monthly archives can use microsecond timestamps. The parser now
  accepts seconds, milliseconds, and microseconds.
- The first Bybit MT4 builder used an incorrect public archive path. The
  corrected builder uses the year directory and month date range, matching the
  official public path shape.
- Bybit spot monthly archives use `id,timestamp,price,volume,side` with
  millisecond timestamps. The trade parser now supports both derivatives
  trading files and spot monthly files.

The previous strict Hyperliquid-only interpretation is out of the central
market-history data-readiness path. Hyperliquid remains preferred when usable,
but central multi-provider data readiness is proven by valid no-paid
manifested data from Hyperliquid, Binance, Bybit, or other eligible
repo-supported providers and must not fail solely because Hyperliquid history
is missing for a symbol/window. This does not close `ISSUE-R106-032` and does
not create Hyperliquid-native autonomous strategy readiness, candidate-pack
evidence, paper/live signals, order placement, sizing instructions,
runtime-mode changes, promotion behavior, or production trading readiness.

Validation passed during this packet:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_central_market_history_store_phase76.py tests/v2/test_central_market_history_collection_phase77.py -q
# 10 passed, 1 StarletteDeprecationWarning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_central_market_history_collection_phase77.py -q
# 6 passed, 1 StarletteDeprecationWarning during parser-fix loop
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_central_market_history_store_phase76.py tests/v2/test_central_market_history_collection_phase77.py tests/v2/test_data_source_registry_phase37.py tests/v2/test_symbol_map_resolver_phase38.py tests/v2/test_universe_data_source_manifest_bridge_phase39.py tests/v2/test_historical_dataset_collection_phase36.py tests/v2/test_bybit_okx_availability_phase55.py tests/v2/test_bybit_okx_fetch_normalize_phase56.py tests/v2/test_binance_vision_availability_phase40.py tests/v2/test_binance_vision_parser_phase41.py tests/v2/test_binance_vision_archive_ingest_phase42.py tests/v2/test_binance_vision_coverage_phase44.py tests/v2/test_binance_vision_downloader_phase45.py tests/v2/test_binance_vision_backfill_phase46.py tests/v2/test_binance_vision_backfill_batch_phase47.py tests/v2/test_binance_derivatives_context_phase48.py tests/v2/test_binance_derivatives_fetch_phase49.py tests/v2/test_binance_derivatives_pagination_phase50.py tests/v2/test_binance_derivatives_archive_ingest_phase51.py tests/v2/test_binance_derivatives_coverage_phase52.py tests/v2/test_binance_derivatives_backfill_phase53.py tests/v2/test_binance_derivatives_worker_phase54.py tests/v2/test_data_quality_phase6.py tests/v2/test_data_family_coverage_gate_phase69.py tests/v2/archive/test_archive_phase4.py tests/v2/archive/test_archive_phase8.py -q
# 135 passed, 1 StarletteDeprecationWarning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts -q
# 463 passed, 1 StarletteDeprecationWarning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2 -q
# 562 passed, 1 StarletteDeprecationWarning
```

Diff hygiene and final boundary scans are recorded in the turn closeout.
