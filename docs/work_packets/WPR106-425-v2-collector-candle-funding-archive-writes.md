# WPR106-425 V2 Collector Candle And Funding Archive Writes

Status: self_checked
Owner: Codex Manager Development Agent
Created: 2026-06-21

## Objective

Replace the remaining recent-candle and funding collector skeleton-only path
with a fixture/source-record archive write path. When a durable collector job is
given local `records`, it must write raw archive data and rebuild bronze/silver
market-data artifacts through the existing archive services. When no records
are provided, the prior diagnostic API-cap warning behavior remains available
for compatibility.

This packet does not add venue/API fetching. It does not create accepted
research evidence, paper/live/order/sizing/runtime, candidate-pack, or
promotion behavior.

## Audit IDs

- `V2-AUD-COLLECT-003`
- `V2-AUD-ARCH-007`
- `V2-AUD-QUAL-003`
- `V2-AUD-WORKER-003`

## Allowed Paths

- `docs/work_packets/WPR106-425-v2-collector-candle-funding-archive-writes.md`
- `docs/contracts/collector_job_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_workers_phase7.py`

## No-Touch Paths

- `src/**/live/**`
- `src/**/runtime.py`
- `run_live_smoke.py`
- `run_manual.py`
- order-placement adapters, broker helpers, exchange submit helpers
- sizing/runtime configuration paths
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `src/tradingbotsuite/promotion/**`
- `src/tradingbotsuite/live/shadow_loader.py`
- committed generated research evidence under `data/research/**`
- legacy GUI/web/operator source paths
- `src/tradingbot/**`
- `.env`, credential files, local SQLite operator DBs, private caches

## Boundary Constraints

- No venue/API calls are allowed; collector write mode consumes only records
  already present in the job input spec.
- The existing no-record diagnostic skeleton path must remain explicitly
  diagnostic and blocked from accepted evidence interpretation.
- Raw writes must use the existing archive layout, raw writer, manifest store,
  and rebuild helpers instead of ad hoc file output.
- Candle collector writes must emit raw, bronze, silver bars, normalization,
  coverage, and optional archive snapshot evidence.
- Funding collector writes must emit raw, bronze, silver funding interval, and
  normalization evidence.
- Durable worker output refs must include archive manifest refs and row counts.
- No generated collector artifacts may be committed.

## Expected Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_workers_phase7.py tests\v2\archive\test_archive_phase8.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Acceptance Criteria

- A `recent_candle_bootstrap` job with local `records` writes a raw candles
  file, rebuilds bronze candles, rebuilds silver bars, writes coverage
  manifests, and can create an archive snapshot.
- A `funding_backfill` job with local `records` writes raw funding, rebuilds
  bronze funding, and rebuilds silver funding intervals.
- Both collector jobs return durable `raw_file_id`, `bronze_file_ids`,
  `silver_file_ids`, and relevant normalization/coverage/snapshot refs.
- The existing no-record recent-candle and funding job behavior still returns
  diagnostic API-cap refs and never claims accepted evidence.
- Control docs record the packet and no autonomous-ready, accepted-evidence,
  paper/live/order/sizing/runtime/promotion claim is created.

## Completion Notes

Implemented and self-checked on 2026-06-21.

Changed files stayed inside the declared packet scope.

Changed files:

- `docs/work_packets/WPR106-425-v2-collector-candle-funding-archive-writes.md`
- `docs/contracts/collector_job_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_workers_phase7.py`

Decisions made:

- Recent-candle and funding collector jobs keep the no-record diagnostic
  API-cap path for compatibility and explicit non-evidence signaling.
- Local-record collector jobs require explicit `archive_root`, `instrument_id`,
  `date`, `start_ts`, and `end_ts` so archive writes are tied to a declared
  job window.
- Collector write mode uses the existing `RawJsonlZstdWriter`,
  `raw_*_to_bronze`, and `bronze_*_to_silver` helpers rather than new ad hoc
  storage logic.
- Candle jobs can request derived timeframes and snapshots; funding jobs write
  funding intervals without adding a coverage policy that does not yet exist
  for funding data.

Acceptance evidence:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_workers_phase7.py tests\v2\archive\test_archive_phase8.py -q
# 14 passed

$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
# 187 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 463 passed

git diff --check
# passed with existing LF-to-CRLF warnings only
```

No venue/API fetch, accepted-evidence artifact, autonomous-ready claim,
candidate-ready claim, paper/live signal, order-placement behavior, sizing
instruction, runtime-mode change, committed generated research evidence, or
promotion-ready artifact was created.
