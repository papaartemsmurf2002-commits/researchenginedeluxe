# WPR106-466 - V2 Durable Lead Book Scan Worker

Status: self_checked
Audit ID: `V2-AUD-LEAD-006`
Related audit IDs: `V2-AUD-WORKER-025`

## Objective

Make the existing read-only Lead Book queue scan runnable through the durable
worker runner as `lead_book_scan`, so manager/scheduler workflows can produce
queue visibility manifests without mutating Lead Book rows, enqueueing
backtests, or implying accepted/autonomous/candidate/paper/live/sizing/runtime/
promotion readiness.

## Allowed Paths

- `docs/work_packets/WPR106-466-v2-lead-book-scan-worker.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/contracts/worker_job_contract.md`
- `docs/contracts/lead_book_contract.md`
- `src/tradingbotsuite/v2/workers/models.py`
- `src/tradingbotsuite/v2/workers/runner.py`
- `src/tradingbotsuite/v2/lead_book/jobs.py`
- `tests/v2/test_lead_book_scan_phase34.py`

## No-Touch Paths

- `src/**/live/**`
- `src/**/runtime.py`
- `run_live_smoke.py`
- `run_manual.py`
- order-placement, broker, exchange-submit, sizing, runtime-config, promotion,
  shadow, and candidate-pack truth-layer paths
- committed `data/research/fixtures/**`
- committed `data/research/historical_cycles/**`
- legacy GUI/operator UI paths
- `src/tradingbot/**`
- `.env`, credential files, local SQLite operator DBs, private caches, and
  unreviewed generated `outputs/**`

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_lead_book_scan_phase34.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Planned Changed Files

- `src/tradingbotsuite/v2/workers/models.py`
- `src/tradingbotsuite/v2/workers/runner.py`
- `src/tradingbotsuite/v2/lead_book/jobs.py`
- `tests/v2/test_lead_book_scan_phase34.py`
- `docs/contracts/worker_job_contract.md`
- `docs/contracts/lead_book_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR106-466-v2-lead-book-scan-worker.md`

## Decisions Made

- `lead_book_scan` is a durable worker job kind, but remains queue visibility
  only. It is not a bounded-cycle required stage and does not replace canonical
  Lead Book or final audit evidence.
- Missing or empty Lead Book queues remain successful worker output with
  blocker refs, matching the existing scan-service contract.
- The worker returns scan manifest refs, queue counts, and blocker refs; it
  does not mutate lead state, request/complete human inspection, approve deep
  validation, enqueue jobs, run backtests, update ledgers, or claim readiness.

## Acceptance Evidence

- Focused Lead Book scan worker/service/CLI regressions:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_lead_book_scan_phase34.py -q`
  passed with `6 passed`.
- V2 baseline:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  passed with `321 passed`.
- Compile baseline:
  `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
  passed.
- Contract baseline:
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  passed with `463 passed`.
- Whitespace check:
  `git diff --check` passed.
- No paper/live/order/sizing/runtime/promotion behavior was added. The new
  worker only writes read-only Lead Book queue visibility manifests and blocker
  refs through the existing scan service.
