# WPR106-488 - V2 Binance Derivatives Archive Ingest

Status: closed - self_checked
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-016`
- `V2-AUD-ARCH-032`

## Objective

Continue `DATA-006` by adding local archive ingest for completed paginated
Binance USD-M derivatives context results. The helper must write raw JSONL.zst
records and generic silver Parquet context rows with source/page provenance,
timestamps, interval/period buckets, numeric fields, unit fields, and
research-only boundary flags.

This packet does not create coverage reports, schedule durable workers, run
backtests, create accepted Hyperliquid-native evidence, create candidate
evidence, create candidate packs, add paper/live behavior, place orders, emit
sizing instructions, change runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-488-v2-binance-derivatives-archive-ingest.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/**`
- `tests/v2/test_binance_derivatives_archive_ingest_phase51.py`

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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_archive_ingest_phase51.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Consume `BinanceDerivativesContextPageResult` values from WPR106-487.
- Refuse blocked or empty page results before writing files.
- Write raw row records before silver rows.
- Store dynamic numeric/unit/raw fields as deterministic JSON strings in the
  generic silver context table; family-specific feature schemas remain later.

## Acceptance Criteria

- Completed paginated context rows write raw and silver archive manifests.
- Blocked or empty page results do not write archive files.
- Missing row timestamps fail closed before writes.
- Archive ingest results preserve source refs, row hashes, file refs, and full
  research-only boundary flags.

## Changed Files

- `docs/work_packets/WPR106-488-v2-binance-derivatives-archive-ingest.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `src/tradingbotsuite/v2/data_sources/binance_derivatives.py`
- `tests/v2/test_binance_derivatives_archive_ingest_phase51.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_archive_ingest_phase51.py -q
# 4 passed
```

Related:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_archive_ingest_phase51.py tests/v2/test_binance_derivatives_pagination_phase50.py tests/v2/test_binance_derivatives_fetch_phase49.py tests/v2/test_binance_derivatives_context_phase48.py tests/v2/test_data_source_registry_phase37.py -q
# 29 passed
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
# 398 passed
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
# 463 passed
git diff --check
# passed with existing LF-to-CRLF working-copy warnings only
```

## Closeout Notes

- Added `ingest_binance_derivatives_context_pages_to_archive()` and
  `BinanceDerivativesContextArchiveIngestResult`.
- Completed page results write raw `derivatives_context` JSONL.zst records
  before generic silver `derivatives_context` Parquet rows.
- Silver rows keep source/page refs, timestamps, publication timestamps,
  interval/period buckets, numeric/unit/raw field JSON, raw file refs, and
  full research-only boundary flags.
- Blocked page results, empty page results, and rows missing timestamps fail
  before archive writes.
- No-touch review: no live runtime, order-placement, sizing, runtime config,
  promotion, shadow, candidate-pack, legacy GUI, secret, or checked legacy
  evidence paths were edited by this packet.

## Follow-up

- `DATA-006` still needs funding/OI/context coverage reports and durable
  worker integration.
