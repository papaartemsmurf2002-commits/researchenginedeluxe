# V2 Audit Report Contract

Status: v2 durable audit/blocker report contract
Audit IDs: `V2-AUD-AUDIT-001`, `V2-AUD-WORKER-009`, `V2-AUD-AUDIT-002`, `V2-AUD-AUDIT-003`, `V2-AUD-AUDIT-004`, `V2-AUD-AUDIT-005`

## Purpose

Audit reports summarize durable research-loop evidence and blockers. They are
triage artifacts, not accepted-research evidence, autonomous-ready
certification, candidate-pack evidence, paper/live signals, order instructions,
sizing instructions, runtime-mode changes, or promotion artifacts.

## Initial Schema Names

- `AuditBlockerReport`
- `AuditJobSummary`
- `AuditReportStatus`

## Required Rules

- Reports must preserve the full v2 research boundary invariant.
- Reports must set `accepted_research_ready=false`.
- Reports must include report ID, run ID, worker job-store path, audited job
  IDs, job status counts, blocker reasons, required next actions, optional
  required successful job-kind criteria, optional required artifact-ref-prefix
  criteria, optional required job-kind order criteria, and artifact refs.
- Job summaries must include enough terminal evidence to audit loop ordering,
  including `finished_at` where present.
- `audit_check` worker jobs must write reports outside ASGI/operator request
  paths through the durable worker runner.
- Report blockers must include failed/stale/cancelled jobs, incomplete targeted
  jobs, gap-record presence, worker `blocker_reasons`, worker `known_blockers`,
  and worker `missing_evidence` refs.
- `audit_check` job specs may declare `required_successful_job_kinds` and
  `required_artifact_ref_prefixes`. These requirements are evaluated only
  against the selected audited jobs and missing items must be reported as
  `missing_evidence:successful_job_kind:<kind>` or
  `missing_evidence:artifact_ref_prefix:<prefix>` blockers.
- `audit_check` job specs may declare `required_job_kind_order`. This
  requirement is evaluated only against successful selected jobs with
  `finished_at` timestamps. Missing ordered kinds must be reported as
  `missing_evidence:loop_order_job_kind:<kind>`, missing timestamps as
  `missing_evidence:loop_order_finished_at:<kind>`, and ordering failures as
  `loop_order_violation:<previous_kind>_after_<kind>` blockers.
- Unknown required job kinds must fail closed before report writes.
- Finding blockers is a successful audit output, not a worker-system failure.
- Generated report files are JSON artifacts and must be hash-addressed in
  worker output refs.
- Secret-like or unsupported report output paths must fail before writes.
- Bounded autopilot cycle plans must generate the final `audit_check` job from
  the declared target job IDs, required successful kinds, required artifact ref
  prefixes, and required job-kind order. A generated audit job remains a queued
  worker job until explicitly run through the durable worker runner.
- Bounded autopilot cycle execution may run that generated final `audit_check`
  job after planned jobs have succeeded, been skipped as already successful, or
  produced explicit blockers. The resulting report remains the cycle blocker
  report and must not mark autonomous readiness even if it has no blockers.

## Forbidden

- Treating audit reports as accepted-research proof or autonomous-ready
  certification.
- Suppressing failed, stale, cancelled, incomplete, gap, blocker, or
  missing-evidence job evidence.
- Writing blocker reports to secret/local-state filenames.
- Producing candidate, paper, live, order, sizing, runtime-mode, or promotion
  claims from audit reports.
- Treating a planned or queued audit job as an audit result.
- Treating a generated audit report with no blockers as sufficient release
  evidence without independent audits, authoritative full-suite validation, real
  archive coverage evidence, and open-blocker closure.
