# WPR106-443 - V2 Official Node Trade Replay Records File

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-COLLECT-014`
- `V2-AUD-XVENUE-011`
- `V2-AUD-ARCH-020`

## Objective

Add a bounded trusted-local replay path for decompressed Hyperliquid official
node fill/trade payload records so durable trade microstructure workers can
normalize those payloads into raw archive trade rows. The path must read only
JSON/JSONL files inside `trusted_source_root`, preserve source hash and
row-count refs, require an official node trade/fill dataset scope, and label
outputs as raw trade replay intake evidence rather than continuous coverage,
queue/fill realism, or accepted research evidence.

This packet does not download from S3, decompress LZ4, normalize node fills
into silver market data, prove historical trade coverage, create accepted
research evidence, create autonomous-ready status, or add paper/live/order/
sizing/runtime/promotion behavior.

## Allowed Paths

- `docs/work_packets/WPR106-443-v2-official-node-trade-replay.md`
- `docs/contracts/archive_contract.md`
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

- Use the existing durable `websocket_trade_capture` worker kind with an
  explicit `source=official_s3_node_trade_replay` mode.
- Require trusted local `records_file` input plus `trusted_source_root`; inline
  `records` are not accepted for this source mode.
- Support only `official_dataset=node_fills_by_block`, `node_fills`, or
  `node_trades`.
- Convert trusted payload records with trade-like fields (`coin`, `time`, `px`,
  `sz`, `side`, `hash`, `tid`) into raw trade microstructure rows.
- Accept simple block/container payloads only when they contain explicit
  `fills`, `trades`, or `data` arrays of trade-like objects.
- Emit dataset, source hash, payload count, trade row count, quality refs,
  storage refs, and replay caveat refs through durable worker outputs.

## Decisions Made

- Added explicit `source=official_s3_node_trade_replay` mode to the existing
  durable `websocket_trade_capture` worker instead of creating a new job kind.
- Required trusted local `records_file` input inside `trusted_source_root` and
  rejected inline `records` for this source mode.
- Allowed only `official_dataset=node_fills_by_block`, `node_fills`, or
  `node_trades`; non-node official datasets fail before archive writes.
- Filtered normalized trade rows to the requested instrument/coin and returned
  skipped-row counts for nonmatching official payload rows.
- Supported direct trade-like records plus simple `fills`, `trades`, or `data`
  container payloads.
- Treated official node ISO timestamps without timezone as UTC inside this
  replay parser only, matching the official L1 data schema examples while
  keeping the behavior local to trusted node replay intake.
- Kept the packet limited to raw trade replay intake: no S3 network download,
  LZ4 decompression, silver normalization, historical coverage acceptance,
  queue/fill realism, accepted research evidence, or paper/live/order/sizing/
  runtime/promotion behavior.

## Changed Files

- `docs/work_packets/WPR106-443-v2-official-node-trade-replay.md`
- `docs/contracts/archive_contract.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_microstructure_collection_phase17.py`

## Acceptance Evidence

- Focused validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_microstructure_collection_phase17.py -q`
  passed with 28 tests.
- Compile validation:
  `python -m compileall -q src/tradingbotsuite` passed.
- Contract validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed with
  463 tests.
- Full v2 validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q` passed with 242 tests.
- Diff hygiene:
  `git diff --check` passed with line-ending warnings only.

## No-Touch Review

- No live runtime, order-placement, sizing, runtime config, promotion,
  candidate-pack truth-layer, legacy GUI, checked historical evidence, secret,
  `.env`, local SQLite operator DB, private cache, or generated runtime output
  path was changed.
- No research artifact was marked accepted, autonomous-ready, candidate-ready,
  promotion-ready, paper-ready, live-ready, order-ready, sizing-ready, or
  signal-ready.
