# V2 Lead Book Contract

Status: v2 Phase 15 Lead Book workflow contract with Phase 20 final-governance links
Audit IDs: `V2-AUD-LEAD-001`, `V2-AUD-FINAL-001`, `V2-AUD-LEAD-004`, `V2-AUD-LEAD-005`

## Purpose

The Lead Book is a non-promotable queue for serious ideas that may deserve
deep validation.

## Initial Schema Names

- `LeadBookRow`
- `LeadState`
- `LeadGateResult`
- `LeadBookScanConfig`
- `LeadBookScanItem`
- `LeadBookScanManifest`
- `LeadBookScanResult`
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
- Durable `lead_book_upsert` worker jobs may create or replace Lead Book rows
  only through the canonical Lead Book service and may emit CSV generated views
  only from the canonical Parquet Lead Book.
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
- Lead Book queue scans are read-only queue visibility artifacts. A scan may
  filter the canonical Lead Book by one or more lead states, write a JSON
  manifest, and report missing or empty queues as blockers. It must not mutate
  lead state, request/complete human inspection, approve deep validation,
  enqueue jobs, run backtests, or claim readiness.

## Forbidden

- Candidate, paper, live, order, sizing, runtime, or promotion claims from a
  lead row.
- Treating projected ROI as proof.
- Starting deep validation without human inspection and agent approval.
- Treating final hard-test survivor state as paper/live/trade readiness.
- Treating worker-generated Lead Book rows or CSV exports as candidate,
  paper/live/order/sizing/runtime, or promotion artifacts.
- Treating a Lead Book scan manifest as strategy performance, validation,
  accepted research evidence, autonomous-readiness proof, candidate-pack
  evidence, or promotion evidence.
