# WPR106-394 V2 Legacy Subsystem Inventory And Classification

Status: closed
Owner: Codex Research Agent
Created: 2026-06-20

## Objective

Implement Phase 3 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`: inspect
and classify the required legacy subsystems before v2 migration reuses or wraps
them.

This packet is audit/classification work only. It does not move, delete,
rewrite, or execute legacy code, configs, generated research artifacts, archive
data, candidate packs, UI code, live/runtime code, strategy code, or promotion
surfaces.

## Audit IDs

- `V2-AUD-LEGACY-001`

## Dependencies

- `docs/V2_LEGACY_CLASSIFICATION.md`
- `docs/V2_NO_TOUCH_PATHS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/ACTIVE_INDEX.md`
- `docs/work_packets/WPR106-393-v2-contract-foundation-and-schema-utilities.md`

## Allowed Paths

- `docs/V2_LEGACY_CLASSIFICATION.md`
- `docs/V2_LEGACY_SUBSYSTEM_AUDIT.md`
- `docs/V2_NO_TOUCH_PATHS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `tests/v2/test_legacy_classification_docs.py`
- `docs/work_packets/WPR106-394-v2-legacy-subsystem-inventory-and-classification.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Do not modify source code, configs, generated data, archives, or artifacts.
- Do not create or modify candidate packs.
- Do not create paper/live artifacts.
- Do not place orders, change runtime mode, write live configuration, or add
  sizing/order-placement behavior.
- Do not relabel legacy evidence as candidate-ready or promotion-ready.

## Acceptance Criteria

- Required legacy subsystems have audit records:
  strict research cycle, candidate-pack gates, rapid sandbox, old high-return
  outputs, rejected rows, strategy plugins, feature builders, existing backtest
  engines, legacy GUI, live/runtime-adjacent code, and old `tradingbot` package.
- Each audit record has files reviewed, purpose, usefulness, risks,
  recommended action, required fixes/follow-up, audit ID, and final status.
- Legacy GUI is marked `freeze_drawer`.
- Live/runtime-adjacent code is marked `no_touch_without_scope`.
- Old outputs are classified as preserved evidence/Lead Book or
  negative-control sources, not rewritten.
- A docs test guards the required subsystem inventory.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
git diff --check
```

No compile or broad pytest validation is required because this packet is
documentation/test-only and does not change implementation files.

## Stop Conditions

- A source/config/generated-data/archive/live/runtime/candidate-pack/promotion
  change becomes necessary.
- A legacy surface must be reused before it has an audit record.

## Completion Notes

Closed on 2026-06-20.

- Updated `docs/V2_LEGACY_CLASSIFICATION.md` to use the roadmap's exact
  classification labels:
  `reuse_as_is`, `reuse_after_fix`, `wrap_into_v2`, `migrate_into_v2`,
  `freeze_drawer`, `move_to_legacy_area`, `no_touch_without_scope`, and
  `remove_later`.
- Added `docs/V2_LEGACY_SUBSYSTEM_AUDIT.md` with records for:
  strict research cycle, candidate-pack gates, rapid sandbox, old high-return
  outputs, rejected rows, strategy plugins, feature builders, existing backtest
  engines, legacy GUI, live/runtime-adjacent code, and old `tradingbot`
  package.
- Marked legacy GUI as `freeze_drawer`.
- Marked live/runtime-adjacent code as `no_touch_without_scope`.
- Classified old high-return outputs and rejected rows as preserved evidence,
  future Lead Book sources, or negative-control/falsification sources; no
  generated data or artifacts were rewritten.
- Extended `docs/V2_NO_TOUCH_PATHS.md` with legacy high-return/rejected output
  preservation.
- Added `tests/v2/test_legacy_classification_docs.py`.
- Marked `V2-AUD-LEGACY-001` as `self_checked` in
  `docs/audit/V2_AUDIT_INDEX.md`.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
git diff --check
```

Result:

- Focused v2 tests passed: 20 passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
- No source, config, generated-data, archive, live/runtime, candidate-pack,
  paper/live, order, sizing, or promotion behavior was changed.
