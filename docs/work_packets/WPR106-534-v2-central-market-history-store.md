# WPR106-534 - V2 Central Market History Store

Status: completed
Owner: Codex Research Agent
Date: 2026-06-25

## Objective

Build a research-only centralized market-history store under
`data/research/central_market_history/**` that discovers, collects or reuses,
normalizes, validates, and manifests no-paid market-history data from eligible
providers. Eligible providers are Hyperliquid, Bybit, Binance, and existing
repo-supported strict-free public providers.

Hyperliquid remains preferred when usable, but centralized market-history
readiness for the multi-provider research lane must not fail solely because
Hyperliquid history is missing. Comparable OHLCV rows from different providers
are equivalent research data when normalized symbol, timeframe, and UTC
timestamps differ by no more than five percent. Larger divergence must keep all
rows with provenance and provider-specific quality status. Orderflow, trade,
and book data must use provenance, schema validity, timestamp sanity,
monotonicity, nonempty rows, and coverage metrics instead of strict
cross-provider equality.

This packet does not create candidate-pack, paper/live, order, sizing,
runtime-mode, promotion, or production trading readiness.

## Allowed Paths

- `docs/work_packets/WPR106-534-v2-central-market-history-store.md`
- `docs/PRODUCT_SCOPE.md`
- `docs/contracts/autonomous_readiness_contract.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/v2/data_sources/central_market_history.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `tests/v2/test_central_market_history_store_phase76.py`
- New generated central market-history artifacts under
  `data/research/central_market_history/**`

## No-Touch Paths

- Live runtime, order-placement, broker/execution, sizing, runtime config,
  promotion, shadow, and candidate-pack truth-layer paths.
- Existing generated research evidence under `data/research/**`, except the
  new `data/research/central_market_history/**` output root.
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

- Add a central market-history storage contract for raw source refs,
  normalized rows, append-only batch manifests, coverage reports, quality
  reports, symbol mapping, checksums, and canonical boundary flags.
- Dedupe by provider, symbol, timeframe, family, and UTC timestamp while
  preserving provenance and source row hashes.
- Add OHLCV equivalence and divergence evaluation with a five percent
  tolerance after normalization.
- Add relaxed orderflow/trade/book quality checks that require provenance,
  schema validity, timestamp sanity, monotonicity, nonempty rows, and coverage
  metrics rather than cross-provider equality.
- Ingest the existing WPR106-533 public Binance/Bybit proxy candle evidence and
  any usable local Hyperliquid public dataset refs into the central store.
- Record exact provider/source/symbol/timeframe blockers for data that is
  missing or excluded by the no-paid/verifiability rules.
- Update control docs to distinguish centralized multi-provider market-history
  readiness from Hyperliquid-native autonomous strategy readiness.

## Expected Validation

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_central_market_history_store_phase76.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_autonomous_readiness_audit_phase29.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2 -q
git diff --check
rg boundary scans for forbidden live/order/sizing/runtime/promotion/candidate-pack drift
```

## Results

Implemented `tradingbotsuite.v2.data_sources.central_market_history` and a
focused phase-76 test suite. The central store preserves the canonical
research-only boundary flags, rejects paid/requester-pays/synthetic/
fixture-only/sandbox-only/supplied-ref/unverifiable sources as accepted
evidence, writes raw JSONL and normalized Parquet outputs, records source
metadata, coverage and quality reports, appends to an append-only manifest,
and refuses to overwrite an existing batch artifact.

Generated batch:

- Root: `data/research/central_market_history/**`
- Batch manifest:
  `data/research/central_market_history/manifests/wpr106-534-central-market-history-e6c053d5bfd69e59-batch_manifest.json`
- Quality report:
  `data/research/central_market_history/manifests/wpr106-534-central-market-history-e6c053d5bfd69e59-quality_report.json`
- Source metadata:
  `data/research/central_market_history/manifests/wpr106-534-central-market-history-e6c053d5bfd69e59-source_metadata.json`
- Source discovery report:
  `data/research/central_market_history/manifests/wpr106-534-central-market-history-source_discovery_report-c598b6f0c1c2.json`
- Append manifest: `data/research/central_market_history/manifests/append_manifest.jsonl`
- Normalized Parquet:
  `data/research/central_market_history/normalized/wpr106-534-central-market-history-e6c053d5bfd69e59.parquet`
- Raw central JSONL:
  `data/research/central_market_history/raw/wpr106-534-central-market-history-e6c053d5bfd69e59.jsonl`

The bounded collection/materialization pass ingested existing WPR106-533
public Binance/Bybit proxy candles, Hyperliquid public `metaAndAssetCtxs` and
recent `candleSnapshot` rows, Binance Vision futures/spot kline archives,
bounded Binance aggTrade/orderflow rows, Bybit public kline API rows, Bybit
MT4 kline archive rows, and bounded Bybit trading archive rows. No paid,
requester-pays, fixture-only, sandbox-only, synthetic, supplied-ref, or
unverifiable data was accepted as evidence. No local secret value was printed,
committed, or persisted.

Batch metrics:

- Input rows: 221560
- Deduped normalized rows: 221462
- Duplicate rows preserved in manifest source hashes: 98
- Providers: 4
- Equivalent OHLCV provider pairs after normalization and <=5 percent price
  tolerance: 31
- Provider-specific OHLCV pairs retained after >5 percent divergence: 30
- `centralized_market_history_ready=true`
- `hyperliquid_missing_not_blocking=true`
- `blocked_provider_count=0` in the generated central quality report

Exact source blockers recorded for the next packet:

- Bybit `premium_index` BTCUSDT archive probe:
  `https://public.bybit.com/premium_index/BTCUSDT/` returned 404.
- Bybit `spot_index` BTCUSDT archive probe:
  `https://public.bybit.com/spot_index/BTCUSDT/` returned 404.
- Bybit spot BTCUSDT January 2024 monthly archive:
  `https://public.bybit.com/spot/BTCUSDT/BTCUSDT-2024-01.csv.gz` was
  reachable but deferred because the raw file size was 89235350 bytes, above
  the bounded pass budget.

Control docs now state that centralized multi-provider market-history data
readiness is separate from Hyperliquid-native autonomous strategy readiness.
`ISSUE-R106-032` remains open because WPR106-534 does not supply accepted
historical as-of Hyperliquid universe refs, accepted Hyperliquid-native
historical coverage proof, bounded-loop strategy evidence, independent audit
evidence, authoritative full-suite evidence, candidate evidence, paper/live
signals, order placement, sizing instructions, runtime-mode changes,
promotion behavior, or production trading readiness.

Validation passed:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_central_market_history_store_phase76.py tests/v2/test_data_source_registry_phase37.py tests/v2/test_symbol_map_resolver_phase38.py tests/v2/test_universe_data_source_manifest_bridge_phase39.py tests/v2/test_historical_dataset_collection_phase36.py tests/v2/test_bybit_okx_availability_phase55.py tests/v2/test_bybit_okx_fetch_normalize_phase56.py tests/v2/test_binance_vision_availability_phase40.py tests/v2/test_binance_vision_parser_phase41.py tests/v2/test_binance_vision_archive_ingest_phase42.py tests/v2/test_binance_vision_coverage_phase44.py tests/v2/test_binance_vision_downloader_phase45.py tests/v2/test_binance_vision_backfill_phase46.py tests/v2/test_binance_vision_backfill_batch_phase47.py tests/v2/test_binance_derivatives_context_phase48.py tests/v2/test_binance_derivatives_fetch_phase49.py tests/v2/test_binance_derivatives_pagination_phase50.py tests/v2/test_binance_derivatives_archive_ingest_phase51.py tests/v2/test_binance_derivatives_coverage_phase52.py tests/v2/test_binance_derivatives_backfill_phase53.py tests/v2/test_binance_derivatives_worker_phase54.py tests/v2/test_data_quality_phase6.py tests/v2/test_data_family_coverage_gate_phase69.py tests/v2/archive/test_archive_phase4.py tests/v2/archive/test_archive_phase8.py -q
# 129 passed, 1 StarletteDeprecationWarning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts -q
# 463 passed, 1 StarletteDeprecationWarning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2 -q
# 556 passed, 1 StarletteDeprecationWarning
git diff --check
# passed with existing LF/CRLF working-copy warnings only
```

Boundary scans over the new central-store implementation, focused tests,
packet, and `data/research/central_market_history/**` artifacts found no
forbidden true-valued candidate, promotion, live, paper, sizing, order, or
runtime boundary flags; no false-valued research/observe flags; and no live
adapter import or order-placement token drift. A broader scan that included all
of `docs/KNOWN_ISSUES.md` surfaced only pre-existing historical issue text
describing old resolved promotion-flag bugs, not WPR106-534 drift.
