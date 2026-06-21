# V2 Audit Report Contract

Status: v2 durable audit/blocker report contract
Audit IDs: `V2-AUD-AUDIT-001`, `V2-AUD-WORKER-009`

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
  criteria, and artifact refs.
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
- Unknown required job kinds must fail closed before report writes.
- Finding blockers is a successful audit output, not a worker-system failure.
- Generated report files are JSON artifacts and must be hash-addressed in
  worker output refs.
- Secret-like or unsupported report output paths must fail before writes.

## Forbidden

- Treating audit reports as accepted-research proof or autonomous-ready
  certification.
- Suppressing failed, stale, cancelled, incomplete, gap, blocker, or
  missing-evidence job evidence.
- Writing blocker reports to secret/local-state filenames.
- Producing candidate, paper, live, order, sizing, runtime-mode, or promotion
  claims from audit reports.
