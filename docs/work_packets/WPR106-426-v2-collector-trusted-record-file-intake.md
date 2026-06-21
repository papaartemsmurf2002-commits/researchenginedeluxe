# WPR106-426 V2 Collector Trusted Record File Intake

Status: self_checked
Owner: Codex Manager Development Agent
Created: 2026-06-21

## Objective

Make durable candle and funding collector archive-write jobs operational from
trusted local record files instead of requiring large inline `records` arrays in
the job input spec. The source-file path must stay inside a declared trusted
root, support bounded JSON/JSONL intake, and record source hash evidence in
worker outputs.

This packet does not add venue/API fetching. It does not create accepted
research evidence, paper/live/order/sizing/runtime, candidate-pack, or
promotion behavior.

## Audit IDs

- `V2-AUD-COLLECT-004`
- `V2-AUD-SEC-006`
- `V2-AUD-WORKER-004`
- `V2-AUD-ARCH-008`

## Allowed Paths

- `docs/work_packets/WPR106-426-v2-collector-trusted-record-file-intake.md`
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

- `records_file` intake must require `trusted_source_root` and use root
  containment checks before reading.
- Only plain JSON arrays and JSONL/NDJSON object files are accepted.
- Secret-like, binary, pickle-like, archive, or arbitrary local files must not
  be read into the archive path.
- Rejected record files must fail the durable job before raw archive files or
  manifest rows are written.
- Inline `records` remain supported for small fixture tests, but a job may not
  specify both inline records and `records_file`.
- Source-file SHA-256 and row count must be visible in durable worker outputs.
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

- Candle collector jobs can read JSONL source records from a trusted root and
  write raw, bronze, silver, coverage, and optional snapshot evidence.
- Funding collector jobs can read JSON array source records from a trusted root
  and write raw, bronze, and silver funding interval evidence.
- Record-file jobs emit `records_source=records_file`,
  `records_file_sha256`, and `records_file_row_count` output refs.
- A record file outside the trusted root, with an unsafe extension, or with an
  invalid record shape fails before archive writes.
- Existing inline-record and no-record diagnostic behavior remains intact.
- Control docs record the packet and no autonomous-ready, accepted-evidence,
  paper/live/order/sizing/runtime/promotion claim is created.

## Completion Notes

Implemented and self-checked on 2026-06-21.

Changed files stayed inside the declared packet scope.

Changed files:

- `docs/work_packets/WPR106-426-v2-collector-trusted-record-file-intake.md`
- `docs/contracts/collector_job_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_workers_phase7.py`

Decisions made:

- `records_file` intake requires `trusted_source_root` rather than accepting
  arbitrary local paths.
- Supported file formats are plain JSON arrays and JSONL/NDJSON object rows.
- The intake rejects secret-like names, unsafe extensions, path escapes,
  oversize files, empty files, and invalid record shapes before calling archive
  writers.
- Successful file-backed jobs include `records_source=records_file`,
  `records_file_sha256`, and `records_file_row_count` in durable output refs.
- Inline records remain supported for compact fixture tests; no-record jobs
  still produce diagnostic API-cap refs.

Acceptance evidence:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_workers_phase7.py tests\v2\archive\test_archive_phase8.py -q
# 20 passed

$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
# 193 passed

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
