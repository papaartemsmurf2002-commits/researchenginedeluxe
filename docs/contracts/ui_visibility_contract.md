# V2 UI Visibility Contract

Status: v2 Phase 22 contract
Audit ID: `V2-AUD-UI-001`

## Purpose

The v2 UI is a read-only visibility surface for research operations. It shows
state that was already produced by v2 services, workers, ledgers, and audit
documents. It does not run collectors, backtests, validation jobs, workers,
order logic, sizing logic, runtime-mode changes, or promotion logic.

## Schema Names

- `V2VisibilitySnapshot`
- `UniverseVisibilityRow`
- `CollectionStatusRow`
- `ArchiveCoverageRow`
- `GapReportRow`
- `LockboxVisibility`
- `LeadBookVisibilityRow`
- `DeepValidationVisibilityRow`
- `FinalHardTestVisibilityRow`
- `AuditChunkVisibilityRow`
- `WorkerJobVisibilityRow`

## Required Sections

The snapshot must be able to represent:

- active universe;
- included and excluded instruments with reasons;
- HIP-3/RWA caveats;
- data collection status;
- archive coverage;
- gap reports;
- lockbox range;
- Lead Book rows and lead state;
- deep validation state;
- final hard-test candidates;
- audit chunk status;
- worker and job health.

## Required Rules

- The snapshot is `research_only`, `observe_only`, and `promotion_ready: false`.
- The UI is read-only and renders from a supplied snapshot.
- Snapshot rendering must escape untrusted text.
- Rendered HTML must not contain forms, buttons, scripts, action links, or
  command controls.
- Output paths must be contained by a configured output root.
- CLI rendering must not run workers, collectors, backtests, validation jobs,
  order placement, sizing logic, runtime-mode mutation, or promotion logic.

## Forbidden

- Legacy GUI behavior defining v2 contracts.
- Running jobs in a UI process.
- Live, paper, order-placement, sizing, runtime-mode, or promotion behavior.
- Candidate-pack creation.
- Trusting snapshot input as executable code.
