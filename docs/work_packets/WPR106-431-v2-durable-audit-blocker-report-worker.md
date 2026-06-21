# WPR106-431 - V2 Durable Audit Blocker Report Worker

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-WORKER-009`
- `V2-AUD-AUDIT-001`

## Purpose

Wire durable audit/blocker reporting into the worker runner by implementing the
existing `audit_check` worker kind. The worker will read durable worker job
records, summarize pass/fail/blocker evidence, and write a research-only JSON
blocker report outside ASGI/operator request paths. This packet does not alter
coverage floors, lockbox policy, accepted-evidence policy, candidate-pack
behavior, Lead Book governance, or any paper/live/order/sizing/runtime
boundary.

## Allowed Paths

- `docs/work_packets/WPR106-431-v2-durable-audit-blocker-report-worker.md`
- `docs/contracts/audit_report_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/audit/schemas.py`
- `src/tradingbotsuite/v2/audit/jobs.py`
- `src/tradingbotsuite/v2/audit/__init__.py`
- `src/tradingbotsuite/v2/workers/runner.py`
- `tests/v2/test_contract_docs.py`
- `tests/v2/test_workers_phase7.py`

## No-Touch Paths

No no-touch path is in scope. This packet must not modify live/runtime/order
placement/sizing/promotion paths, candidate-pack truth-layer paths, generated
research evidence, legacy GUI paths, old `tradingbot` compatibility code,
secrets, credential files, or unreviewed local state.

## Decisions Made

- Use the existing `audit_check` worker kind for durable blocker reporting
  rather than adding another worker enum.
- Write canonical blocker reports as JSON artifacts under the caller-supplied
  output path; do not treat the report as accepted-research proof or
  autonomous-ready certification.
- Summarize only durable job-store evidence, including failed/stale/cancelled
  jobs, incomplete targeted jobs, job gap records, `blocker_reasons`,
  `known_blockers`, and `missing_evidence` refs surfaced by prior workers.
- Treat blockers as report evidence, not worker-system failure. The worker
  should fail only when it cannot safely read inputs or write the report.
- Reject secret-like or unsupported report output paths before writing.
- Defer final autonomous-ready certification, independent audit execution, and
  real venue/API operation to later scoped packets.

## Expected Tests

- Focused:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py tests/v2/test_contract_docs.py -q`
- Broad v2:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
- Baseline:
  - `python -m compileall -q src/tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- Hygiene:
  - `git diff --check`

## Changed Files

- `docs/work_packets/WPR106-431-v2-durable-audit-blocker-report-worker.md`
- `docs/contracts/audit_report_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/audit/schemas.py`
- `src/tradingbotsuite/v2/audit/jobs.py`
- `src/tradingbotsuite/v2/audit/__init__.py`
- `src/tradingbotsuite/v2/workers/runner.py`
- `tests/v2/test_contract_docs.py`
- `tests/v2/test_workers_phase7.py`

## Acceptance Evidence

- Focused worker smoke:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py -q`
  - Result: `27 passed`
- Focused worker/contract-doc lane:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py tests/v2/test_contract_docs.py -q`
  - Result: `29 passed`
- Broad v2:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  - Result: `205 passed`
- Baseline compile:
  - `python -m compileall -q src/tradingbotsuite`
  - Result: passed
- Contract baseline:
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  - Result: `463 passed`
- Diff hygiene:
  - `git diff --check`
  - Result: passed with existing LF-to-CRLF working-copy warnings only

## Boundary Statement

The packet remains research-only and observe-only. It must not create accepted
evidence by itself, autonomous-ready status, candidate-pack eligibility,
paper/live/order/sizing/runtime behavior, or promotion readiness. A blocker
report is triage evidence and cannot override the v2 completion checklist,
independent audit requirement, or authoritative full-suite validation
requirement.
