# WPR106-440 - V2 Hyperliquid Official File Scope Guard

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-COLLECT-011`
- `V2-AUD-XVENUE-008`
- `V2-AUD-ARCH-017`

## Objective

Tighten durable `official_s3_backfill` jobs for Hyperliquid official historical
files so trusted local raw-file preservation cannot imply unsupported historical
datasets or normalized coverage evidence. The worker must classify documented
Hyperliquid official file datasets, return that scope through durable output
refs, and fail before archive writes when a Hyperliquid job claims unsupported
official candle/spot-style datasets.

This packet supports raw native historical-file preservation only. It does not
download from S3, normalize L2 or node fills into silver market data, prove
historical candle coverage, prove historical trade coverage, create accepted
research evidence, create autonomous-ready status, or add paper/live/order/
sizing/runtime/promotion behavior.

## Allowed Paths

- `docs/work_packets/WPR106-440-v2-hyperliquid-official-file-scope.md`
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

- Keep network downloads out of this packet; source files must already be
  trusted local files inside `trusted_source_root`.
- For `venue=hyperliquid`, require either an explicit supported
  `official_dataset` or an inferable documented source path.
- Supported Hyperliquid raw official-file scopes are limited to:
  `market_data_l2_book`, `asset_ctxs`, `node_fills_by_block`, `node_fills`, and
  `node_trades`.
- Reject unsupported Hyperliquid official-file claims such as `candles`,
  `ohlcv`, or spot asset data before archive writes.
- Return dataset, scope, endpoint, adapter, file hash, and raw-native caveat
  refs through durable worker outputs.

## Decisions Made

- Kept `official_s3_backfill` as a trusted local-file preservation worker and
  did not add S3 network downloads in this packet.
- Scoped Hyperliquid official raw-file intake to documented historical file
  families useful for v2 archive work: L2 book snapshots, asset contexts, and
  node fill/trade files.
- Made Hyperliquid official-file jobs fail closed when a spec claims unsupported
  official candle/OHLCV/spot-style datasets.
- Added durable output refs for source endpoint, adapter, raw file SHA-256,
  official dataset, official dataset scope, no-network-download status, and the
  raw-native/non-normalized caveat.
- Left normalization from official raw files into silver market data for later
  packets; this packet only prevents misleading raw-file evidence.

## Changed Files

- `docs/work_packets/WPR106-440-v2-hyperliquid-official-file-scope.md`
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
  - Result: `17 passed`
- Compile:
  - `python -m compileall -q src/tradingbotsuite`
  - Result: passed
- Contracts:
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  - Result: `463 passed`
- Full v2 suite:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  - Result: `231 passed`
- Diff hygiene:
  - `git diff --check`
  - Result: passed with existing LF-to-CRLF warnings only.

## No-Touch Review

- No no-touch path was edited.
- No live runtime, order-placement, sizing, runtime config, promotion,
  candidate-pack truth-layer, legacy GUI, checked `data/research/**` evidence,
  secret, credential, local DB, or private cache path was touched.
- The worker reads only trusted local source files inside `trusted_source_root`
  and writes raw native archive files plus manifest refs. It performs no S3
  network download and does not normalize official files into coverage evidence.
- The packet adds no accepted-evidence, autonomous-ready, candidate-ready,
  paper/live/order/sizing/runtime, or promotion behavior.
