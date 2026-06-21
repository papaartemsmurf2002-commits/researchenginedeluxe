# WPR106-442 - V2 Official Asset Contexts Replay Records File

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-COLLECT-013`
- `V2-AUD-XVENUE-010`
- `V2-AUD-ARCH-019`

## Objective

Add a bounded trusted-local replay path for decompressed Hyperliquid official
`asset_ctxs` payload records so durable official-file jobs can write raw
asset-context archive rows and rebuild bronze plus silver context tables. The
path must read only JSON/JSONL files inside `trusted_source_root`, preserve
source hash and row-count refs, require `official_dataset=asset_ctxs`, and
label outputs as context replay intake evidence rather than continuous coverage
or accepted research evidence.

This packet does not download from S3, decompress LZ4, normalize candles,
normalize node fills/trades, create accepted research evidence, create
autonomous-ready status, or add paper/live/order/sizing/runtime/promotion
behavior.

## Allowed Paths

- `docs/work_packets/WPR106-442-v2-official-asset-ctxs-replay.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_microstructure_collection_phase17.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, or
  candidate-pack truth-layer paths.
- No legacy GUI paths.
- No checked historical evidence under `data/research/**`.
- No secrets, `.env`, local SQLite operator DBs, private cache, or generated
  runtime output paths.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_microstructure_collection_phase17.py -q
```

Baseline:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
git diff --check
```

## Implementation Notes

- Use the existing durable `official_s3_backfill` worker kind with an explicit
  `source=official_s3_asset_ctxs_replay` mode.
- Require trusted local `records_file` input plus `trusted_source_root`; inline
  `records` are not accepted for this source mode.
- Support JSON arrays, JSONL/NDJSON objects, and JSON files shaped like
  Hyperliquid `metaAndAssetCtxs`/asset-context payloads after trusted-root
  resolution.
- Write raw `asset_contexts` archive records before rebuilding bronze and
  silver context tables through existing archive services.
- Emit dataset, source hash, payload count, row counts, raw/bronze/silver, and
  normalization refs through durable worker outputs.

## Decisions Made

- Added `source=official_s3_asset_ctxs_replay` to the existing durable
  `official_s3_backfill` worker instead of adding a new worker kind.
- Required trusted local `records_file` input and rejected inline `records` for
  this source mode, preserving source-file hash and row-count provenance.
- Required `official_dataset=asset_ctxs` and failed closed for other
  Hyperliquid official dataset scopes before archive writes.
- Reused existing raw, bronze, and silver `asset_contexts` archive services
  after source-specific trusted JSON/JSONL payload normalization.
- Supported Hyperliquid meta/context JSON shape by converting the meta
  universe names into context rows before archive normalization.
- Kept network download, LZ4 decompression, continuous-context-coverage
  claims, coverage acceptance, evidence-readiness, and paper/live/order/
  sizing/runtime/promotion behavior out of scope.

## Changed Files

- `docs/work_packets/WPR106-442-v2-official-asset-ctxs-replay.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_microstructure_collection_phase17.py`

## Acceptance Evidence

- Focused microstructure/official-file validation:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_microstructure_collection_phase17.py -q`
  - Result: `24 passed`
- Compile:
  - `python -m compileall -q src/tradingbotsuite`
  - Result: passed
- Contracts:
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  - Result: `463 passed`
- Full v2 suite:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  - Result: `238 passed`
- Diff hygiene:
  - `git diff --check`
  - Result: passed with existing LF-to-CRLF warnings only.

## No-Touch Review

- No no-touch path was edited.
- No live runtime, order-placement, sizing, runtime config, promotion,
  candidate-pack truth-layer, legacy GUI, checked `data/research/**` evidence,
  secret, credential, local DB, or private cache path was touched.
- The worker reads only trusted local JSON/JSONL payload files inside
  `trusted_source_root`; it performs no S3 download and no LZ4 decompression.
- The packet adds no accepted-evidence, autonomous-ready, candidate-ready,
  paper/live/order/sizing/runtime, or promotion behavior.
