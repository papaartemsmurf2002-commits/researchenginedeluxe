# WPR106-437 - V2 Worker Store Import Boundary

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-PKG-002`
- `V2-AUD-TESTINFRA-002`
- `V2-AUD-WORKER-010`
- `V2-AUD-ARCH-014`

## Purpose

Resolve `ISSUE-R106-029` by removing the eager `run_data_quality_job` import
from `tradingbotsuite.v2.data_quality.__init__` while preserving the public
package export. A fresh interpreter must be able to import
`WorkerJobStore` directly for standalone worker scripts and smoke utilities.
This packet does not change worker job behavior, archive data, validation
floors, lockbox policy, coverage floors, strategy semantics, paper/live/order/
sizing/runtime behavior, candidate-pack behavior, or promotion behavior.

## Allowed Paths

- `docs/work_packets/WPR106-437-v2-worker-store-import-boundary.md`
- `docs/KNOWN_ISSUES.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/archive/__init__.py`
- `src/tradingbotsuite/v2/data_quality/__init__.py`
- `tests/v2/test_import_boundaries_phase25.py`

## No-Touch Paths

No live/runtime/order placement/sizing/promotion path is in scope. This packet
must not modify worker persistence semantics, collector behavior, generated
research evidence, candidate-pack truth-layer paths, legacy GUI paths, old
`tradingbot` compatibility code, secrets, credential files, lockbox policy,
coverage floors, date floors, or no-touch path policy.

## Decisions Made

- Keep existing data-quality package exports for coverage helpers and schemas.
- Make only `run_data_quality_job` a lazy package-level export, because importing
  it eagerly pulls in `WorkerJobStore` through `data_quality.jobs`.
- Add a fresh-interpreter regression that imports `WorkerJobStore` before any
  data-quality module ordering side effects.
- Add a compatibility regression proving
  `from tradingbotsuite.v2.data_quality import run_data_quality_job` still
  resolves to a callable job dispatcher.
- Resolve `ISSUE-R106-029` only if focused, v2, contracts, compile, and diff
  hygiene validation pass.

## Expected Tests

- Focused:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_import_boundaries_phase25.py -q`
- Broad v2:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
- Baseline:
  - `python -m compileall -q src/tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- Hygiene:
  - `git diff --check`

## Changed Files

- `docs/work_packets/WPR106-437-v2-worker-store-import-boundary.md`
- `docs/KNOWN_ISSUES.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/archive/__init__.py`
- `src/tradingbotsuite/v2/data_quality/__init__.py`
- `tests/v2/test_import_boundaries_phase25.py`

## Acceptance Evidence

- Focused import-boundary lane:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_import_boundaries_phase25.py -q`
  - Result: `2 passed`
- Broad v2:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  - Result: `224 passed`
- Baseline compile:
  - `python -m compileall -q src/tradingbotsuite`
  - Result: passed
- Contract baseline:
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  - Result: `463 passed`
- Diff hygiene:
  - `git diff --check`
  - Result: passed with existing LF-to-CRLF working-copy warnings only
- Original fresh-interpreter smoke:
  - `$env:PYTHONPATH='src'; python -c "from tradingbotsuite.v2.workers.job_store import WorkerJobStore; from tradingbotsuite.v2.data_quality import run_data_quality_job; print(WorkerJobStore.__name__, callable(run_data_quality_job))"`
  - Result: `WorkerJobStore True`

## Boundary Statement

The packet remains research-only and observe-only. It only changes package
import timing and regression coverage; it must not create accepted-evidence
status, autonomous-ready status, candidate-pack eligibility, paper/live/order/
sizing/runtime behavior, or promotion readiness.
