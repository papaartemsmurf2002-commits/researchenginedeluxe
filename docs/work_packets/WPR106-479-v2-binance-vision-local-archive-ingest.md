# WPR106-479 - V2 Binance Vision Local Archive Ingest

Status: closed - self_checked
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-007`
- `V2-AUD-ARCH-028`

## Objective

Continue the `DATA-005` Binance Vision slice by ingesting already-available
local ZIP bytes through the WPR106-478 parser into the v2 archive pipeline. The
packet writes raw archive records for parsed Binance Vision rows, writes
bronze/silver 1m kline bars, and writes raw trade/aggTrade microstructure
captures with parser diagnostics preserved.

This packet does not perform network downloads, implement cache management,
run reconstructed-bar comparisons, create accepted research evidence, create
candidate evidence, write candidate packs, add paper/live behavior, place
orders, emit sizing instructions, mutate runtime mode, or create promotion
claims.

## Allowed Paths

- `docs/work_packets/WPR106-479-v2-binance-vision-local-archive-ingest.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/**`
- `tests/v2/test_binance_vision_archive_ingest_phase42.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No legacy GUI paths.
- No checked legacy evidence under `data/research/fixtures/**`,
  `data/research/historical_cycles/**`, or existing WPR evidence directories.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_vision_archive_ingest_phase42.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Input is ZIP bytes and optional checksum payload; no HTTP fetcher.
- Use existing `RawJsonlZstdWriter`, `write_parquet_rows`, and
  microstructure capture helpers.
- Klines become raw records plus bronze candles and silver 1m bars.
- Trades and aggTrades become raw records and raw microstructure trade capture
  rows with Binance-native IDs preserved in parser metadata.
- Parser diagnostics must be returned and written as manifest metadata.

## Acceptance Criteria

- Valid kline ZIP bytes write raw, bronze, and silver archive file refs.
- Valid trade/aggTrade ZIP bytes write raw archive file refs and
  microstructure quality/storage refs.
- Parser checksum, duplicate, gap, monotonicity, and interval diagnostics are
  preserved in the ingest result.
- All output refs remain research-only/non-promotable and non-native to
  Hyperliquid.

## Changed Files

- `docs/work_packets/WPR106-479-v2-binance-vision-local-archive-ingest.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `src/tradingbotsuite/v2/data_sources/binance_vision.py`
- `tests/v2/test_binance_vision_archive_ingest_phase42.py`

## Acceptance Evidence

Focused validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_binance_vision_archive_ingest_phase42.py -q
# 2 passed
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_binance_vision_archive_ingest_phase42.py tests\v2\test_binance_vision_parser_phase41.py tests\v2\test_binance_vision_availability_phase40.py tests\v2\test_universe_data_source_manifest_bridge_phase39.py tests\v2\test_data_source_registry_phase37.py tests\v2\test_symbol_map_resolver_phase38.py -q
# 34 passed
```

Baseline validation:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
# passed
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
# 364 passed
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 463 passed
git diff --check
# passed with existing LF-to-CRLF warnings only
```

## No-Touch Review

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer path was changed.
- No legacy GUI path was changed.
- No checked legacy evidence under `data/research/fixtures/**` or
  `data/research/historical_cycles/**` was rewritten.
- The packet ingests in-memory/local ZIP bytes only and performs no network
  download or downloader/cache operation.
- The packet creates no accepted research, autonomous-ready, candidate-ready,
  paper/live/order/sizing/runtime, or promotion claim.

## Follow-Up

- A later `DATA-005` packet should integrate availability manifests with an
  actual downloader/cache and then produce coverage reports.
- Reconstructed kline-vs-trade/aggTrade comparison remains a pending
  fail-closed quality gate.
