# WPR106-481 - V2 Binance Vision Data-Family Coverage Reports

Status: closed - self_checked
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-009`
- `V2-AUD-QUAL-009`

## Objective

Continue `DATA-005` by generating contract-level `DataFamilyCoverageReport`
objects for Binance Vision daily availability, parser, ingest, and reconstructed
bar comparison evidence. The reports must record per-symbol/source/family/date
coverage gaps and blocker reasons without treating Binance data as
Hyperliquid-native coverage.

This packet does not perform network downloads, mutate live/runtime state, run
backtests, create accepted Hyperliquid-native evidence, create candidate
evidence, create candidate packs, add paper/live behavior, place orders, emit
sizing instructions, or create promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-481-v2-binance-vision-data-family-coverage.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/contracts/data_family_coverage_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/**`
- `tests/v2/test_binance_vision_coverage_phase44.py`

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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_vision_coverage_phase44.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Coverage report inputs are existing Binance Vision availability rows,
  parse results, ingest results, and optional reconstructed-bar comparison
  reports.
- Daily expected bucket counts are 1 for availability/trade-family date
  presence and 1440 for 1m kline bucket coverage.
- Missing ZIPs, mapping blockers, parser warnings, duplicate IDs, kline gaps,
  ingest absences, and failed reconstructed-bar comparison must become explicit
  `reason` metadata.
- Reports must use `CoverageLabel.EXTERNAL_COMPARISON` and
  `native_to_hyperliquid=false` semantics; accepted reports cannot imply
  Hyperliquid-native fills.

## Acceptance Criteria

- Available, parsed, ingested, and reconstruction-passed Binance Vision daily
  klines can produce an accepted external-comparison coverage report when 1m
  buckets meet the configured coverage floor and no blockers remain.
- Missing availability, unverified mappings, parser gaps/duplicates, missing
  ingest evidence, and reconstruction failures produce non-accepted coverage
  reports with deterministic missing-bucket/reason metadata.
- Coverage report IDs are stable for identical inputs and boundary flags remain
  research-only.

## Changed Files

- `docs/work_packets/WPR106-481-v2-binance-vision-data-family-coverage.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/contracts/data_family_coverage_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `src/tradingbotsuite/v2/data_sources/binance_vision.py`
- `tests/v2/test_binance_vision_coverage_phase44.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_vision_coverage_phase44.py -q
# 4 passed
```

Related:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_vision_coverage_phase44.py tests/v2/test_binance_vision_reconstruction_phase43.py tests/v2/test_binance_vision_archive_ingest_phase42.py tests/v2/test_binance_vision_parser_phase41.py tests/v2/test_binance_vision_availability_phase40.py tests/v2/test_universe_data_source_manifest_bridge_phase39.py tests/v2/test_data_source_registry_phase37.py tests/v2/test_symbol_map_resolver_phase38.py -q
# 41 passed
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
# 371 passed
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
# 463 passed
git diff --check
# passed with existing LF-to-CRLF working-copy warnings only
```

## Closeout Notes

- Added `build_binance_vision_data_family_coverage_report()` as the
  deterministic bridge from Binance Vision availability/parser/ingest/
  comparison metadata to `DataFamilyCoverageReport`.
- Full archived and reconstructed 1m kline days can be accepted only as
  `external_comparison` coverage; the report does not claim Hyperliquid-native
  fills or execution truth.
- Missing mappings, ZIPs, parser output, ingest/archive refs, available-but-
  unverified checksums, duplicates, kline gaps, partial 1m buckets, and failed
  reconstructed-bar comparison become blocker reasons.
- No-touch review: no live runtime, order-placement, sizing, runtime config,
  promotion, shadow, candidate-pack, legacy GUI, secret, or checked legacy
  evidence paths were edited by this packet.

## Follow-up

- `DATA-005` still needs downloader/cache integration and report-write/job
  orchestration for complete Binance Vision backfill operation.
