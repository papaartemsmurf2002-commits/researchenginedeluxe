# WPR106-446 - V2 Audit Required Loop Evidence

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-AUDIT-002`
- `V2-AUD-WORKER-013`
- `V2-AUD-AUTONOMY-004`

## Objective

Make durable `audit_check` jobs able to verify that a manager-selected research
loop has required successful job kinds and required artifact refs before a
blocker report can pass. Missing universe/archive/coverage/backtest/ledger/
Lead Book evidence must become explicit `missing_evidence:*` blocker output
instead of being absent from the report.

This packet does not certify autonomous readiness, change evidence floors,
change lockbox/date policy, fetch venue data, mutate archives, run backtests,
write ledger or Lead Book rows, or add paper/live/order/sizing/runtime/
promotion behavior.

## Allowed Paths

- `docs/work_packets/WPR106-446-v2-audit-required-loop-evidence.md`
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

- Add optional audit job spec fields for required successful job kinds and
  required artifact-ref prefixes.
- Evaluate required evidence only across the selected audited jobs.
- Invalid required job-kind values must fail closed before writing the report.
- Missing successful job kinds must produce
  `missing_evidence:successful_job_kind:<kind>` blockers.
- Missing artifact-ref prefixes must produce
  `missing_evidence:artifact_ref_prefix:<prefix>` blockers.
- Keep reports non-certifying with `accepted_research_ready=false`.

## Decisions Made

- Added optional `required_successful_job_kinds` to `audit_check` input specs.
- Added optional `required_artifact_ref_prefixes` to `audit_check` input specs.
- Evaluated required evidence only against the selected audited job set.
- Reported missing successful job kinds as
  `missing_evidence:successful_job_kind:<kind>`.
- Reported missing artifact-ref prefixes as
  `missing_evidence:artifact_ref_prefix:<prefix>`.
- Kept reports non-certifying with `accepted_research_ready=false`, including
  when all selected required evidence is present and report status is `pass`.
- Added report fields for the required successful job-kind and artifact-ref
  prefix criteria so the report JSON and report ID reflect the checklist being
  audited.
- Failed unknown required job-kind values before writing a report.
- Did not add scheduling, venue fetching, archive mutation, backtest execution,
  ledger writes, Lead Book writes, readiness certification, or boundary-policy
  changes.

## Changed Files

- `docs/work_packets/WPR106-446-v2-audit-required-loop-evidence.md`
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
  passed with 45 tests.
- Compile validation:
  `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite` passed.
- Contract validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed with
  463 tests.
- Full v2 validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q` passed with 252 tests.
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
