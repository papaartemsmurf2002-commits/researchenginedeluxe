# V2 Legacy Classification

Status: v2 contract foundation
Audit ID: `V2-AUD-LEGACY-001`
Source: `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`

Legacy code, configs, UI, and artifacts are not automatically obsolete and are
not automatically v2 core. Reuse requires a classification row.

## Labels

- `reuse_as_is`: safe and useful with no material change.
- `reuse_after_fix`: useful but needs bug, security, or contract repair first.
- `wrap_into_v2`: useful behavior behind a v2 interface.
- `migrate_into_v2`: move responsibility into a v2 bounded context.
- `freeze_drawer`: keep available but outside the default v2 path.
- `move_to_legacy_area`: explicitly mark or relocate as legacy.
- `no_touch_without_scope`: live/runtime/evidence-sensitive; requires a scoped
  packet before edits.
- `remove_later`: delete only after replacement and audit.

## Audit Record Schema

Initial Python schema name planned: `LegacyAuditRecord`.

Required fields:

- `legacy_id`
- `path`
- `recommended_action`
- `reason`
- `risk_flags`
- `required_followup`
- `research_only`
- `candidate_evidence`
- `promotion_ready`
- `auditor`
- `audit_id`

## Rules

Legacy high-return rows can become Lead Book sources only. Rejected rows can
become negative-control or falsification sources. Neither can become candidate
evidence, paper/live signals, sizing instructions, order-placement
instructions, runtime-mode changes, or promotion evidence.
