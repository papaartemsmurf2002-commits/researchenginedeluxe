# WPR106-482 - V2 Binance Vision Downloader Cache

Status: closed - self_checked
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-010`
- `V2-AUD-ARCH-029`

## Objective

Continue `DATA-005` by adding a bounded Binance Vision downloader/cache helper
that consumes one available strict-free availability row, downloads ZIP and
checksum bytes through an injectable client, verifies checksums when present,
writes deterministic local cache files under the archive root, and writes a
small download manifest.

This packet does not add background job orchestration, run broad backfills,
call live/order systems, mutate runtime mode, run backtests, create accepted
Hyperliquid-native evidence, create candidate evidence, create candidate packs,
add paper/live behavior, place orders, emit sizing instructions, or create
promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-482-v2-binance-vision-downloader-cache.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/**`
- `tests/v2/test_binance_vision_downloader_phase45.py`

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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_vision_downloader_phase45.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Input is an existing `BinanceVisionAvailabilityRow`.
- The default HTTP client may use public GET requests, but tests must inject a
  fake client and perform no network access.
- Cache paths must stay archive-root-contained and deterministic by
  source/symbol/date/family.
- Checksum files are downloaded only when availability marked them available.
- Non-available rows, HTTP errors, max-byte violations, and checksum mismatch
  must become explicit blocker result metadata.

## Acceptance Criteria

- A successful download writes ZIP bytes, optional checksum bytes, and a
  manifest with byte counts, SHA-256 hashes, cache refs, checksum verification,
  and research-only boundary flags.
- Re-running against the same cache path reuses cached bytes without a network
  call and preserves stable result identity.
- Missing/non-available rows and checksum mismatch fail closed with explicit
  statuses and reasons.

## Changed Files

- `docs/work_packets/WPR106-482-v2-binance-vision-downloader-cache.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `src/tradingbotsuite/v2/data_sources/binance_vision.py`
- `tests/v2/test_binance_vision_downloader_phase45.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_vision_downloader_phase45.py -q
# 3 passed
```

Related:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_vision_downloader_phase45.py tests/v2/test_binance_vision_coverage_phase44.py tests/v2/test_binance_vision_reconstruction_phase43.py tests/v2/test_binance_vision_archive_ingest_phase42.py tests/v2/test_binance_vision_parser_phase41.py tests/v2/test_binance_vision_availability_phase40.py tests/v2/test_universe_data_source_manifest_bridge_phase39.py tests/v2/test_data_source_registry_phase37.py tests/v2/test_symbol_map_resolver_phase38.py -q
# 44 passed
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
# 374 passed
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
# 463 passed
git diff --check
# passed with existing LF-to-CRLF working-copy warnings only
```

## Closeout Notes

- Added `download_binance_vision_availability_row_to_cache()` with an
  injectable GET client and deterministic archive-root-contained raw cache
  paths for ZIP/checksum payloads.
- Added `BinanceVisionDownloadResult`, `BinanceVisionDownloadStatus`, and
  `BinanceVisionGetResult`.
- Successful downloads and cache hits preserve stable payload identity and
  write source-download manifests; checksum mismatch, unavailable rows, HTTP
  errors, and byte-cap violations fail closed.
- No-touch review: no live runtime, order-placement, sizing, runtime config,
  promotion, shadow, candidate-pack, legacy GUI, secret, or checked legacy
  evidence paths were edited by this packet.

## Follow-up

- `DATA-005` still needs report-write/job orchestration and multi-day backfill
  coordination that chains availability -> download/cache -> parse -> ingest
  -> comparison -> data-family coverage reports.
