# WPR106-430 - V2 Durable Lead Book Worker

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-WORKER-008`
- `V2-AUD-LEAD-004`

## Purpose

Wire non-promotable Lead Book upsert operations into the durable worker runner
so ledger-backed research ideas can be recorded outside ASGI/operator request
paths. This packet does not alter Lead Book schema governance, human
inspection requirements, deep-validation policy, final hard-test policy,
coverage floors, lockbox policy, candidate-pack behavior, or any
paper/live/order/sizing/runtime boundary.

## Allowed Paths

- `docs/work_packets/WPR106-430-v2-durable-lead-book-worker.md`
- `docs/contracts/worker_job_contract.md`
- `docs/contracts/lead_book_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/lead_book/jobs.py`
- `src/tradingbotsuite/v2/lead_book/__init__.py`
- `src/tradingbotsuite/v2/workers/models.py`
- `src/tradingbotsuite/v2/workers/runner.py`
- `tests/v2/test_workers_phase7.py`

## No-Touch Paths

No no-touch path is in scope. This packet must not modify live/runtime/order
placement/sizing/promotion paths, candidate-pack truth-layer paths, generated
research evidence, legacy GUI paths, old `tradingbot` compatibility code,
secrets, credential files, or unreviewed local state.

## Decisions Made

- Implement `lead_book_upsert` as the durable worker kind for creating or
  replacing one non-promotable Lead Book row.
- Reuse `create_lead_from_source`, `LeadBookStore.upsert`, and
  `LeadBookStore.export_csv`; do not duplicate Lead Book row construction,
  human-inspection validation, ROI-not-claim semantics, or gate checks.
- Treat invalid source artifacts, unsupported/secret-like paths, or Lead Book
  validation failures as worker failures because the upsert did not occur.
- Use ledger Parquet files and run manifests as acceptable source artifacts for
  this packet; broader trusted source-file intake remains out of scope.
- Return Lead Book path/hash, lead ID, source hash, non-promotable state, and
  optional generated CSV refs through worker output evidence.
- Defer blocker-report worker orchestration and real venue/API collection to
  later scoped packets.

## Expected Tests

- Focused:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py tests/v2/test_lead_book_phase15.py -q`
- Broad v2:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
- Baseline:
  - `python -m compileall -q src/tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- Hygiene:
  - `git diff --check`

## Changed Files

- `docs/work_packets/WPR106-430-v2-durable-lead-book-worker.md`
- `docs/contracts/worker_job_contract.md`
- `docs/contracts/lead_book_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/lead_book/jobs.py`
- `src/tradingbotsuite/v2/lead_book/__init__.py`
- `src/tradingbotsuite/v2/workers/models.py`
- `src/tradingbotsuite/v2/workers/runner.py`
- `tests/v2/test_workers_phase7.py`

## Acceptance Evidence

- Focused worker smoke:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py -q`
  - Result: `25 passed`
- Focused worker/Lead Book lane:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py tests/v2/test_lead_book_phase15.py -q`
  - Result: `35 passed`
- Broad v2:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  - Result: `203 passed`
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
paper/live/order/sizing/runtime behavior, or promotion readiness. Lead Book
rows created by the worker remain non-promotable leads and still require human
inspection plus explicit agent approval before deep-validation workflow states.
