# V2 Autonomous Readiness Contract

Status: v2 manager-gate contract
Audit IDs: `V2-AUD-COMPLETE-002`, `V2-AUD-AUDIT-006`

## Purpose

The autonomous readiness gate turns the execution brief's final manager
checklist into a deterministic JSON blocker report. It is a repo-completion
gate for supplied evidence, not a strategy-quality certificate, accepted
research result, candidate pack, paper/live signal, order instruction, sizing
instruction, runtime-mode change, or promotion artifact.

## Schema Names

- `AutonomousReadinessEvidence`
- `ReadinessEvidenceItem`
- `AutonomousReadinessReport`
- `ReadinessCheckSummary`
- `AutonomousReadinessStatus`

## Required Evidence Inputs

- One readiness evidence JSON object using
  `autonomous_readiness_evidence_v1`.
- Exactly one evidence item for each required checklist key. Missing,
  duplicate, unexpected, failed, or reference-less items must block readiness.
- Optional evidence item paths may be supplied; if supplied, the path must
  exist.
- A bounded-cycle execution manifest path proving the operational loop ran
  through universe, archive, coverage, backtest, ledger, Lead Book, and final
  audit job kinds.
- A final durable audit/blocker report path. The final audit report must parse
  as `AuditBlockerReport`, have `status=pass`, have no blockers, and keep
  `accepted_research_ready=false`.
- A canonical append-only ledger path containing at least one row.
- A canonical Lead Book path containing at least one row.
- Open P0 and P1 counts. Any open P0 or P1 count blocks autonomous readiness.

## Required Rules

- Reports must preserve the full v2 research boundary invariant.
- Reports must set `promotion_ready=false`,
  `candidate_pack_eligible=false`, `paper_signal=false`, `live_signal=false`,
  `sizing_instruction=false`, `order_placement_instruction=false`, and
  `runtime_mode_change=false`.
- Reports must use `autonomous_readiness_report_v1` and include report ID, run
  ID, created timestamp, status, required-check count, passed-check count,
  blocker count, blocker reasons, required-check keys, per-check summaries,
  artifact refs, and required next actions.
- The status may be `autonomous_research_ready` only when all required
  checklist items pass, all required artifacts exist, the cycle execution
  manifest is completed and audited, the final audit report passes, the ledger
  and Lead Book are nonempty, and P0/P1 counts are zero.
- Any missing or failed evidence must produce `status=blocked` and
  `autonomous_research_ready=false`.
- Generated report files are JSON artifacts and must reject secret-like or
  unsupported output paths before writes.
- A passing readiness report for synthetic test fixtures proves gate semantics
  only. A real manager completion claim still requires real evidence paths and
  current validation evidence.

## Forbidden

- Treating readiness reports as accepted research evidence, strategy
  profitability evidence, candidate-pack evidence, paper/live signal output,
  order instructions, sizing instructions, runtime-mode changes, or promotion
  artifacts.
- Inferring readiness from a queued plan, an unrun audit job, a fixture-only
  sandbox cycle, or a blocker-containing audit report.
- Suppressing missing real-archive, validation, independent-audit, ledger, Lead
  Book, open-issue, or loop-execution blockers.
- Weakening coverage floors, date floors, lockbox policy, no-touch paths,
  credential policy, data-licensing boundaries, or candidate/promotion
  language through readiness evidence.
