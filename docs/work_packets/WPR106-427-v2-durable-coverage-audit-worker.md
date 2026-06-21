# WPR106-427 V2 Durable Coverage Audit Worker

Status: self_checked
Owner: Codex Manager Development Agent
Created: 2026-06-21

## Objective

Implement the durable `coverage_audit` worker job kind so a queued job can
audit a local archive silver bars file, write coverage and quality manifests,
and return blocker evidence through durable worker output refs. This closes the
next operational-loop gap after collector archive writes: archive -> coverage
audit must be worker-runnable rather than only a direct CLI/service call.

This packet does not add venue/API fetching. It does not create paper/live,
order, sizing, runtime, candidate-pack, or promotion behavior.

## Audit IDs

- `V2-AUD-WORKER-005`
- `V2-AUD-QUAL-004`
- `V2-AUD-ARCH-009`

## Allowed Paths

- `docs/work_packets/WPR106-427-v2-durable-coverage-audit-worker.md`
- `docs/contracts/worker_job_contract.md`
- `docs/contracts/data_quality_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `src/tradingbotsuite/v2/data_quality/jobs.py`
- `src/tradingbotsuite/v2/data_quality/__init__.py`
- `src/tradingbotsuite/v2/workers/runner.py`
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

- The job must read local archive manifest rows and local Parquet data only.
- The job must not fetch data, mutate live/runtime state, or infer strategy
  readiness.
- The job must succeed when it successfully writes an audit report even if the
  report contains coverage or quality blockers.
- The job must fail before report writes if the requested file ID is missing or
  is not a silver bars file.
- Default worker evidence mode is `sandbox_diagnostic` unless the caller
  explicitly sets a different data-quality evidence mode.
- No generated coverage artifacts may be committed.

## Expected Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_workers_phase7.py tests\v2\test_data_quality_phase6.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Acceptance Criteria

- `run_one_job(..., kind=coverage_audit, ...)` runs a durable coverage audit.
- A valid silver bars file ID writes `data_coverage.parquet` and
  `data_quality_checks.parquet`.
- Worker output refs include `coverage_report_id`, `quality_check_ids`,
  `coverage_ratio`, `quality_status`, `evidence_eligible`, and
  `blocker_reasons`.
- Low-coverage or quality-failing data is recorded as blocker evidence without
  turning the worker job into a system failure.
- Missing or non-silver-bars file IDs fail closed without writing reports.
- Control docs record the packet and no autonomous-ready, paper/live/order/
  sizing/runtime/promotion claim is created.

## Completion Notes

Implemented and self-checked on 2026-06-21.

Changed files stayed inside the declared packet scope.

Changed files:

- `docs/work_packets/WPR106-427-v2-durable-coverage-audit-worker.md`
- `docs/contracts/worker_job_contract.md`
- `docs/contracts/data_quality_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `src/tradingbotsuite/v2/data_quality/jobs.py`
- `src/tradingbotsuite/v2/data_quality/__init__.py`
- `src/tradingbotsuite/v2/workers/runner.py`
- `tests/v2/test_workers_phase7.py`

Decisions made:

- The coverage-audit implementation lives in `tradingbotsuite.v2.data_quality`
  rather than the collector package because it is an archive quality step, not
  source collection.
- The worker accepts archive `file_id` or `silver_file_id`, but it requires the
  resolved manifest row to be a silver bars file.
- Default worker evidence mode is `sandbox_diagnostic`; callers must explicitly
  request another data-quality evidence mode.
- Low coverage and quality failures are represented as report blocker evidence
  while the worker job succeeds if the audit itself completes.
- Missing or non-silver-bars file IDs fail before coverage/quality manifest
  writes.

Acceptance evidence:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_workers_phase7.py tests\v2\test_data_quality_phase6.py -q
# 24 passed

$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
# 196 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 463 passed

git diff --check
# passed with existing LF-to-CRLF warnings only
```

No venue/API fetch, autonomous-ready claim, candidate-ready claim, paper/live
signal, order-placement behavior, sizing instruction, runtime-mode change,
committed generated research evidence, or promotion-ready artifact was created.
