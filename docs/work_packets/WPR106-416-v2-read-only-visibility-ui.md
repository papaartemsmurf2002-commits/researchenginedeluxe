# WPR106-416 V2 Read-Only Visibility UI

Status: closed
Owner: Codex Research Agent
Created: 2026-06-21

## Objective

Implement Phase 22 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md` as a
read-only v2 visibility surface, separate from the legacy GUI. The UI renders a
static dashboard snapshot showing universe, collection, coverage, gap,
lockbox, Lead Book, deep validation, final hard-test, audit, and worker/job
health sections without running collectors, backtests, validation jobs, or
workers inside a UI process.

This packet does not modify legacy GUI/web/operator paths, run collectors, run
backtests, write generated research evidence beyond explicitly requested local
HTML output, create candidate packs, place orders, produce paper/live signals,
emit sizing instructions, change runtime mode, or create promotion-ready
artifacts.

## Audit IDs

- `V2-AUD-UI-001`

## Dependencies

- WPR106-413 Phase 22 deferral/scope packet.
- `docs/V2_FUTURE_UI_DEFERRAL.md`
- Existing v2 CLI boundary pattern.
- Existing v2 path policy and security hygiene.

## Allowed Paths

- `docs/contracts/ui_visibility_contract.md`
- `docs/V2_FUTURE_UI_DEFERRAL.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/ui/**`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/**`
- `docs/work_packets/WPR106-416-v2-read-only-visibility-ui.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- The v2 UI must be static/read-only from a supplied snapshot.
- No legacy GUI/web/operator paths may be changed.
- No UI process may run collectors, workers, backtests, validation jobs, order
  logic, sizing logic, runtime-mode mutation, or promotion logic.
- Output paths must be root-contained.
- The rendered UI must not include forms, buttons, scripts, action links, or
  command controls.
- Research-only, observe-only, non-promotable semantics must be visible in the
  snapshot contract.

## Acceptance Criteria

- A schema-backed `V2VisibilitySnapshot` can represent every Phase 22 required
  visibility section.
- HTML rendering escapes untrusted values and emits a static read-only page.
- CLI rendering reads a snapshot JSON file and writes root-contained static
  HTML without running jobs.
- Tests prove boundary flags, section coverage, output-root containment,
  read-only markup, escaping, audit row visibility, and CLI rendering.
- `V2-AUD-UI-001` moves from planned to self_checked only after validation.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_ui_visibility_phase22.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Use a browser/HTML verification pass for a rendered fixture if practical in
the local environment.

## Stop Conditions

- A legacy GUI/web/operator path must be modified.
- UI implementation needs a live server that can run jobs in-process.
- Snapshot rendering cannot be kept read-only.
- A live/runtime/order/sizing/promotion implication appears.

## Completion Notes

Closed on 2026-06-21.

- Added `docs/contracts/ui_visibility_contract.md`.
- Added the read-only v2 UI package:
  - `V2VisibilitySnapshot`;
  - universe, collection, coverage, gap, lockbox, Lead Book, deep validation,
    final hard-test, audit, and worker/job row schemas;
  - escaped static HTML rendering;
  - root-contained HTML writing.
- Added `redx ui render`, which reads a root-contained snapshot JSON file and
  writes root-contained static HTML.
- Added focused Phase 22 UI tests covering all required sections, boundary flag
  rejection, non-promotable Lead Book rows, lockbox enforcement, escaping,
  read-only markup, output-root containment, CLI rendering, input-root
  containment, and audit-row visibility.
- Updated Phase 22 docs and moved `V2-AUD-UI-001` to `self_checked`.
- No legacy GUI/web/operator path, job-running UI process, generated research
  evidence, candidate pack, paper/live signal, sizing instruction, order
  placement, runtime-mode change, promotion behavior, or live-runtime import
  was introduced.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_ui_visibility_phase22.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Result:

- Focused Phase 22 UI tests passed: 13 passed.
- Full v2 tests passed: 169 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- Full `compileall` for `src\tradingbotsuite` passed.
- Contract tests passed: 462 passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.

Browser/HTML smoke:

- Rendered a fixture `V2VisibilitySnapshot` to static HTML.
- Served it over local HTTP with `python -m http.server`.
- Verified with Playwright CLI that the page title was
  `ResearchEngineDeluxe v2 Visibility`.
- Verified required sections `Active Universe`, `Final Hard Tests`, and
  `Workers` were present.
- Verified forbidden interactive markup count for
  `script, form, button, a[href], [onclick]` was zero.
