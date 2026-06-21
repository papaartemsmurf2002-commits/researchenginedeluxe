# WPR106-429 - V2 Durable Ledger Append Export Worker

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-WORKER-007`
- `V2-AUD-LEDGER-004`

## Purpose

Wire canonical ledger append/export operations into the durable worker runner so
backtest pass/fail run manifests can be logged outside ASGI/operator request
paths. This packet does not alter ledger schema, accepted-evidence floors,
Lead Book state, validation policy, lockbox policy, coverage floors,
candidate-pack behavior, or any paper/live/order/sizing/runtime boundary.

## Allowed Paths

- `docs/work_packets/WPR106-429-v2-durable-ledger-append-export-worker.md`
- `docs/contracts/worker_job_contract.md`
- `docs/contracts/ledger_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/ledger/jobs.py`
- `src/tradingbotsuite/v2/ledger/__init__.py`
- `src/tradingbotsuite/v2/workers/runner.py`
- `tests/v2/test_workers_phase7.py`

## No-Touch Paths

No no-touch path is in scope. This packet must not modify live/runtime/order
placement/sizing/promotion paths, candidate-pack truth-layer paths, generated
research evidence, legacy GUI paths, old `tradingbot` compatibility code,
secrets, credential files, or unreviewed local state.

## Decisions Made

- Implement `ledger_append_export` as the durable worker kind for canonical
  ledger append and optional generated CSV/XLSX exports.
- Reuse `append_run_to_ledger` and `export_ledger`; do not duplicate ledger
  row construction or accepted-research gates.
- Treat duplicate run IDs and ledger validation failures as worker failures
  because they mean the append operation did not occur.
- Add worker-boundary suffix/name guards for ledger and export paths so job
  specs cannot accidentally write `.env`, credential-like names, or unsupported
  output types.
- Defer Lead Book updates to a later scoped packet because Lead Book rows have
  distinct gate summaries, human-inspection semantics, and non-promotable lead
  workflow ownership.

## Expected Tests

- Focused:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py tests/v2/test_ledger_phase13.py -q`
- Broad v2:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
- Baseline:
  - `python -m compileall -q src/tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- Hygiene:
  - `git diff --check`

## Changed Files

- `docs/work_packets/WPR106-429-v2-durable-ledger-append-export-worker.md`
- `docs/contracts/worker_job_contract.md`
- `docs/contracts/ledger_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/ledger/jobs.py`
- `src/tradingbotsuite/v2/ledger/__init__.py`
- `src/tradingbotsuite/v2/workers/runner.py`
- `tests/v2/test_workers_phase7.py`

## Acceptance Evidence

- Focused worker smoke:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py -q`
  - Result: `22 passed`
- Focused worker/ledger lane:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py tests/v2/test_ledger_phase13.py -q`
  - Result: `30 passed`
- Broad v2:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  - Result: `200 passed`
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
evidence by itself, autonomous-ready status, candidate-pack eligibility, Lead
Book promotion, paper/live/order/sizing/runtime behavior, or promotion
readiness.
