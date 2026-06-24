# WPR106-484 - V2 Binance Vision Backfill Batch Coordination

Status: closed - self_checked
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-012`
- `V2-AUD-ARCH-031`

## Objective

Finish the local, non-worker `DATA-005` Binance Vision chain by adding a
bounded batch helper that consumes an availability manifest, selects target
rows for one source ID, matches optional comparison rows by symbol/date, runs
daily backfill orchestration, and writes a batch manifest with summary counts.

This packet does not add durable worker scheduling, run broad unattended
backfills, call live/order systems, mutate runtime mode, run backtests, create
accepted Hyperliquid-native evidence, create candidate evidence, create
candidate packs, add paper/live behavior, place orders, emit sizing
instructions, or create promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-484-v2-binance-vision-backfill-batch-coordination.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/**`
- `tests/v2/test_binance_vision_backfill_batch_phase47.py`

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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_vision_backfill_batch_phase47.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Input is an existing `BinanceVisionAvailabilityManifest`.
- The helper selects target rows by `source_id`, optionally matches comparison
  rows by `(binance_symbol, probe_date)`, and calls
  `run_binance_vision_daily_backfill()` per selected row.
- Batch size must be bounded by a `max_rows` cap.
- The batch manifest must record completed/blocked/accepted counts and result
  IDs without hiding individual blockers.

## Acceptance Criteria

- A manifest containing matching kline/trade rows can run a bounded batch and
  write a batch manifest with completed/accepted counts.
- Blocked rows remain visible as blocked daily results and batch blocker counts.
- Result identity, manifest refs, and boundary flags are deterministic and
  research-only.

## Changed Files

- `docs/work_packets/WPR106-484-v2-binance-vision-backfill-batch-coordination.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `src/tradingbotsuite/v2/data_sources/binance_vision.py`
- `tests/v2/test_binance_vision_backfill_batch_phase47.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_vision_backfill_batch_phase47.py -q
# 2 passed
```

Related:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_vision_backfill_batch_phase47.py tests/v2/test_binance_vision_backfill_phase46.py tests/v2/test_binance_vision_downloader_phase45.py tests/v2/test_binance_vision_coverage_phase44.py tests/v2/test_binance_vision_reconstruction_phase43.py tests/v2/test_binance_vision_archive_ingest_phase42.py tests/v2/test_binance_vision_parser_phase41.py tests/v2/test_binance_vision_availability_phase40.py tests/v2/test_universe_data_source_manifest_bridge_phase39.py tests/v2/test_data_source_registry_phase37.py tests/v2/test_symbol_map_resolver_phase38.py -q
# 49 passed
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
# 379 passed
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
# 463 passed
git diff --check
# passed with existing LF-to-CRLF working-copy warnings only
```

## Closeout Notes

- Added `run_binance_vision_backfill_batch()` and
  `BinanceVisionBackfillBatchResult`.
- The helper consumes an availability manifest, selects target rows by source
  ID, matches optional comparison rows by symbol/date, runs daily backfill
  under a `max_rows` cap, and writes batch manifests under
  `manifests/binance_vision_backfills/`.
- Completed, blocked, and accepted counts plus aggregate blockers are preserved
  without adding durable worker scheduling or unattended broad backfills.
- No-touch review: no live runtime, order-placement, sizing, runtime config,
  promotion, shadow, candidate-pack, legacy GUI, secret, or checked legacy
  evidence paths were edited by this packet.

## Follow-up

- `DATA-005` still needs durable worker integration before unattended
  operational use; the local data chain is otherwise ready for bounded callers.
