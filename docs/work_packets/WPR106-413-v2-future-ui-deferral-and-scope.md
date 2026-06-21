# WPR106-413 V2 Future UI Deferral And Scope

Status: closed
Owner: Codex Research Agent
Created: 2026-06-21

## Objective

Handle Phase 22 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md` as a
deliberate deferral rather than an early UI build. This packet records the
future v2 UI visibility scope, the no-early-build rules, and the conditions
for opening a later implementation packet.

This packet does not build UI, modify legacy GUI/web paths, run collectors,
run backtests, write generated research evidence, create candidate packs, place
orders, produce paper/live signals, emit sizing instructions, change runtime
mode, or create promotion-ready artifacts.

## Audit IDs

- `V2-AUD-UI-001`

## Dependencies

- Phase 22 roadmap section.
- Completed v2 foundation packets through Phase 21.
- `docs/V2_NO_TOUCH_PATHS.md` legacy GUI no-touch rule.

## Allowed Paths

- `docs/V2_FUTURE_UI_DEFERRAL.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-413-v2-future-ui-deferral-and-scope.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Do not modify legacy GUI/web/operator paths.
- Do not run collectors, backtests, validation jobs, or workers from a UI
  process.
- Do not let legacy GUI shape v2 contracts or behavior.
- Future UI must be visibility-first until a later explicit packet scopes
  command surfaces and worker delegation.
- Preserve research-only, observe-only, non-promotable semantics.

## Acceptance Criteria

- `V2-AUD-UI-001` is registered as deferred/planned, not implemented.
- Future UI scope lists the required visibility surfaces from Phase 22.
- No-early-build stop conditions are documented.
- The document states that a later UI packet must name no-touch paths, command
  boundaries, tests, and worker delegation before any UI implementation.
- No source code, legacy GUI, live/runtime/order/sizing path, generated
  evidence, candidate pack, paper/live signal, or promotion behavior is changed.

## Validation

```powershell
git diff --check
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

No broader tests are required because this packet is documentation-only and
does not change source code or shared contracts.

## Stop Conditions

- Any UI source path must be changed.
- Any legacy GUI/web/operator path must be changed.
- Any command-running UI behavior is required.
- The deferral would hide an active P0/P1 safety issue.

## Completion Notes

Closed on 2026-06-21.

- Added `docs/V2_FUTURE_UI_DEFERRAL.md`.
- Registered `V2-AUD-UI-001` as `planned` in the audit index, with Phase 22
  explicitly deferred by design rather than implemented early.
- Documented future visibility surfaces, no-early-build constraints, and
  prerequisites for a later implementation packet.
- No UI source, legacy GUI/web/operator path, source code, generated research
  evidence, candidate pack, paper/live signal, sizing instruction, order
  placement, runtime-mode change, promotion behavior, or live-runtime import
  was changed.

Validation:

```powershell
git diff --check
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Result:

- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
- Full `compileall` for `src\tradingbotsuite` passed.
- Contract tests passed: 462 passed.
