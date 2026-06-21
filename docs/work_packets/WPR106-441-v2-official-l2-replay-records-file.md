# WPR106-441 - V2 Official L2 Replay Records File

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-COLLECT-012`
- `V2-AUD-XVENUE-009`
- `V2-AUD-ARCH-018`

## Objective

Add a bounded trusted-local replay path for decompressed Hyperliquid official
`l2Book` payload records so durable BBO/L2 microstructure workers can normalize
those payloads into archive rows. The path must read only JSON/JSONL files
inside `trusted_source_root`, preserve source hash and row-count refs, reject
non-`market_data_l2_book` official datasets, and label outputs as raw
microstructure replay evidence rather than continuous capture or accepted
coverage evidence.

This packet does not download from S3, decompress LZ4, normalize candles,
normalize node fills/trades, create silver coverage, create accepted research
evidence, create autonomous-ready status, or add paper/live/order/sizing/
runtime/promotion behavior.

## Allowed Paths

- `docs/work_packets/WPR106-441-v2-official-l2-replay-records-file.md`
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

- Use the existing durable `websocket_l2_bbo_capture` worker kind with an
  explicit `source=official_s3_l2_replay` mode.
- Support `datatype=bbo` and `datatype=l2` only.
- Require `records_file` plus `trusted_source_root`; inline `records` are not
  accepted for this source mode.
- Reuse existing JSON/JSONL records-file containment and parsing policy.
- Normalize each Hyperliquid `l2Book` payload through the same parser as the
  public `/info` L2 snapshot path, but stamp rows with an official replay
  source label.
- Emit dataset, source hash, payload count, row count, storage, quality, and
  raw replay caveat refs through durable worker outputs.

## Decisions Made

- Added `source=official_s3_l2_replay` to the existing durable
  `websocket_l2_bbo_capture` worker instead of adding a new worker kind.
- Required trusted local `records_file` input and rejected inline `records` for
  this source mode, preserving source-file hash and row-count provenance.
- Reused the public `l2Book` payload parser but stamped replay rows with
  `official_s3/market_data_l2_book` source provenance.
- Restricted replay to `datatype=bbo` or `datatype=l2` and
  `official_dataset=market_data_l2_book`; node fills/trades and asset contexts
  remain separate future normalization work.
- Kept network download, LZ4 decompression, continuous-capture claims, coverage
  acceptance, and evidence-readiness out of scope.

## Changed Files

- `docs/work_packets/WPR106-441-v2-official-l2-replay-records-file.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_microstructure_collection_phase17.py`

## Acceptance Evidence

- Focused microstructure validation:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_microstructure_collection_phase17.py -q`
  - Result: `21 passed`
- Compile:
  - `python -m compileall -q src/tradingbotsuite`
  - Result: passed
- Contracts:
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  - Result: `463 passed`
- Full v2 suite:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  - Result: `235 passed`
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
