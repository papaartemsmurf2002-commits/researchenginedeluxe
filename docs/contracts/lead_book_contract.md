# V2 Lead Book Contract

Status: v2 Phase 15 Lead Book workflow contract with Phase 20 final-governance links
Audit IDs: `V2-AUD-LEAD-001`, `V2-AUD-FINAL-001`

## Purpose

The Lead Book is a non-promotable queue for serious ideas that may deserve
deep validation.

## Initial Schema Names

- `LeadBookRow`
- `LeadState`
- `LeadGateResult`
- `HumanInspectionStatus`
- `AgentApprovalStatus`
- `TradeCountSummary`
- `MonthlyStabilitySummary`
- `PnlConcentrationSummary`

## Required Rules

- Leads are not candidates.
- Rows include lead ID, source type, source refs, family, thesis, venue/symbol
  scope, data window, assumptions, observed ROI, projected ROI, blockers,
  missing evidence, required next validation, human inspection status, agent
  approval status, and boundary metadata.
- Lead promotion gates require human inspection and agent approval.
- Lead rows require observed ROI, projected ROI, projection assumptions, and
  `roi_projection_is_not_claim: true`.
- Lead rows are stored canonically as Parquet; CSV is a generated view.
- Deep validation requests require completed human inspection and explicit
  agent approval after that inspection.
- Gate checks fail six losing months in a year, fewer than five average trades
  per month, missing minimum usable months, and excessive profit concentration.
- Gate checks warn on profit concentration above warning thresholds and
  diminishing returns.
- Pre-2024 diagnostic fallback rows without fallback metadata are marked
  failed/blocked.
- Deep-validation and final hard-test lead states remain governance states only;
  they do not make a lead a candidate, paper/live signal, sizing instruction,
  order instruction, runtime-mode change, or promotion artifact.
- Final hard-test consideration requires the validation contract's one-active
  deep-validation lock, max-three final-slot rule, frozen evidence fields, and
  non-live survivor report disclaimer.

## Forbidden

- Candidate, paper, live, order, sizing, runtime, or promotion claims from a
  lead row.
- Treating projected ROI as proof.
- Starting deep validation without human inspection and agent approval.
- Treating final hard-test survivor state as paper/live/trade readiness.
