# WPR106-447 - V2 Audit Loop Order Evidence

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-AUDIT-003`
- `V2-AUD-WORKER-014`
- `V2-AUD-AUTONOMY-005`

## Objective

Make durable `audit_check` jobs able to verify that a manager-selected
research loop has successful job kinds in the required operational order. A
blocker report may already require successful job kinds and artifact refs; this
packet adds optional loop-order proof so an out-of-order universe/archive/
coverage/backtest/ledger/Lead Book chain cannot pass by coincidence.

This packet does not certify autonomous readiness, change evidence floors,
change lockbox/date policy, fetch venue data, mutate archives, run backtests,
write ledger or Lead Book rows, or add paper/live/order/sizing/runtime/
promotion behavior.

## Allowed Paths

- `docs/work_packets/WPR106-447-v2-audit-loop-order-evidence.md`
- `docs/contracts/audit_report_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/audit/schemas.py`
- `src/tradingbotsuite/v2/audit/jobs.py`
- `tests/v2/test_workers_phase7.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, or
  candidate-pack truth-layer paths.
- No legacy GUI paths.
- No checked historical evidence under `data/research/**`.
- No secrets, `.env`, local SQLite operator DBs, private cache, or generated
  runtime output paths.
- No lockbox, coverage-floor, date-floor, no-touch-path, credential,
  licensing, or candidate/promotion language policy changes.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
git diff --check
```

## Implementation Notes

- Add optional audit job spec field `required_job_kind_order`.
- Evaluate required order only across the selected audited jobs.
- Required order proof uses successful jobs with `finished_at` timestamps.
- Missing required ordered kinds must produce
  `missing_evidence:loop_order_job_kind:<kind>` blockers.
- Missing timestamps for an otherwise present kind must produce
  `missing_evidence:loop_order_finished_at:<kind>` blockers.
- Out-of-order successful jobs must produce
  `loop_order_violation:<previous_kind>_after_<kind>` blockers.
- Unknown required ordered job-kind values must fail closed before writing the
  report.
- Keep reports non-certifying with `accepted_research_ready=false`.

## Decisions Made

- Added optional `required_job_kind_order` to `audit_check` input specs.
- Evaluated required order only against the selected audited job set.
- Matched ordered stages using successful jobs with nondecreasing
  `finished_at` timestamps.
- Reported absent ordered stages as
  `missing_evidence:loop_order_job_kind:<kind>`.
- Reported successful ordered stages without completion timestamps as
  `missing_evidence:loop_order_finished_at:<kind>`.
- Reported out-of-order stages as
  `loop_order_violation:<previous_kind>_after_<kind>`.
- Added `required_job_kind_order` to the report schema, report identity, and
  audit worker output refs.
- Added `finished_at` to job summaries so reports expose the timestamp evidence
  used for order checks.
- Failed unknown ordered job-kind values before writing a report.
- Kept reports non-certifying with `accepted_research_ready=false`, including
  when a selected ordered loop passes.
- Did not add scheduling, venue fetching, archive mutation, backtest execution,
  ledger writes, Lead Book writes, readiness certification, or boundary-policy
  changes.

## Changed Files

- `docs/work_packets/WPR106-447-v2-audit-loop-order-evidence.md`
- `docs/contracts/audit_report_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/audit/schemas.py`
- `src/tradingbotsuite/v2/audit/jobs.py`
- `tests/v2/test_workers_phase7.py`

## Acceptance Evidence

- Focused validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py -q`
  passed with 47 tests.
- Compile validation:
  `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite` passed.
- Contract validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed with
  463 tests.
- Full v2 validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q` passed with 254 tests.
- Diff hygiene:
  `git diff --check` passed with line-ending warnings only.

## No-Touch Review

- No live runtime, order-placement, sizing, runtime config, promotion,
  candidate-pack truth-layer, legacy GUI, checked historical evidence, secret,
  `.env`, local SQLite operator DB, private cache, or generated runtime output
  path was changed.
- No lockbox policy, coverage floor, date floor, no-touch path, credential,
  data licensing, candidate/promotion language, or legacy evidence deletion
  decision was changed.
- No research artifact was marked autonomous-ready, candidate-ready,
  promotion-ready, paper-ready, live-ready, order-ready, sizing-ready,
  signal-ready, accepted historical coverage proof, or unattended continuous
  capture proof.
