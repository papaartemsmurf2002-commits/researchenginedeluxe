# WPR106-483 - V2 Binance Vision Daily Backfill Orchestration

Status: closed - self_checked
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-011`
- `V2-AUD-ARCH-030`
- `V2-AUD-QUAL-010`

## Objective

Finish the local `DATA-005` Binance Vision chain by adding a bounded daily
orchestration helper that connects availability rows to downloader/cache,
parser, archive ingest, optional reconstructed-bar comparison, and data-family
coverage report writing.

This packet does not add a durable worker queue, run broad backfills, call
live/order systems, mutate runtime mode, run backtests, create accepted
Hyperliquid-native evidence, create candidate evidence, create candidate packs,
add paper/live behavior, place orders, emit sizing instructions, or create
promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-483-v2-binance-vision-daily-backfill-orchestration.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/contracts/data_family_coverage_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/**`
- `tests/v2/test_binance_vision_backfill_phase46.py`

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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_vision_backfill_phase46.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Input is one target `BinanceVisionAvailabilityRow` and optional comparison
  source row for kline reconstruction checks.
- The helper downloads/caches, parses cached ZIP bytes, ingests parsed target
  rows into the archive, optionally compares trade/aggTrade reconstruction to
  target klines, builds a `DataFamilyCoverageReport`, and writes it under
  `manifests/coverage_reports/`.
- Download, parse, ingest, comparison, and coverage blockers must be surfaced
  in result metadata rather than hidden.
- The helper may accept an existing archive snapshot ref; creating durable
  snapshot/job orchestration remains later work.

## Acceptance Criteria

- A complete daily kline backfill with a passing comparison writes a coverage
  report ref and accepted external-comparison coverage when all acceptance
  inputs are present.
- Non-available downloads, checksum mismatch, parse/ingest/comparison failures,
  and missing archive snapshot refs produce blocked results and non-accepted
  coverage reports.
- Result identity, output refs, and boundary flags are deterministic and
  research-only.

## Changed Files

- `docs/work_packets/WPR106-483-v2-binance-vision-daily-backfill-orchestration.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/contracts/data_family_coverage_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `src/tradingbotsuite/v2/data_sources/binance_vision.py`
- `tests/v2/test_binance_vision_backfill_phase46.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_vision_backfill_phase46.py -q
# 3 passed
```

Related:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_vision_backfill_phase46.py tests/v2/test_binance_vision_downloader_phase45.py tests/v2/test_binance_vision_coverage_phase44.py tests/v2/test_binance_vision_reconstruction_phase43.py tests/v2/test_binance_vision_archive_ingest_phase42.py tests/v2/test_binance_vision_parser_phase41.py tests/v2/test_binance_vision_availability_phase40.py tests/v2/test_universe_data_source_manifest_bridge_phase39.py tests/v2/test_data_source_registry_phase37.py tests/v2/test_symbol_map_resolver_phase38.py -q
# 47 passed
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
# 377 passed
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
# 463 passed
git diff --check
# passed with existing LF-to-CRLF working-copy warnings only
```

## Closeout Notes

- Added `run_binance_vision_daily_backfill()` and
  `BinanceVisionDailyBackfillResult`.
- The helper chains one target row through download/cache, parse, target archive
  ingest, optional reconstructed-bar comparison, and data-family coverage JSON
  writing under `manifests/coverage_reports/`.
- Completed rows can return accepted external-comparison coverage only when all
  coverage gates pass. Blocked rows still write non-accepted coverage reports
  with explicit blockers.
- No-touch review: no live runtime, order-placement, sizing, runtime config,
  promotion, shadow, candidate-pack, legacy GUI, secret, or checked legacy
  evidence paths were edited by this packet.

## Follow-up

- `DATA-005` still needs durable worker integration and multi-day backfill
  coordination across availability manifests and symbol-map rows.
