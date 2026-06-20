# Work Packet: WPR106-58 Catalog Refresh Reuse Default

## Goal

Fix the operator Research tab behavior where clicking `Refresh Catalog`
surprises the operator by starting a new full historical catalog collection
job when a candidate-depth R106 catalog is already available. The default UI
action should reuse/check the active catalog and only rebuild when the operator
explicitly asks for a rebuild.

## Current Repo Facts

- Current branch: `main`.
- WPR106-57 has uncommitted UI visibility edits in the same working tree.
- The backend already detects candidate-depth catalog readiness for autopilot
  and skips catalog refresh when ready.
- The standalone `Refresh Historical Catalog` button posts directly to
  `/api/operator/research/jobs/refresh-historical-data-catalog`, which queues a
  new isolated refresh job.

## Allowed Edit Paths

- `docs/work_packets/WPR106-58-*.md`
- `src/tradingbotsuite/web/templates/research.html`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/operator_console.py`
- `tests/tradingbotsuite/test_operator_ui.py`

## Research Boundary

- This packet changes operator job semantics and UI wording only.
- Do not change data collection math, fixture validation thresholds,
  candidate gates, research algorithms, generated historical evidence, paper or
  live runtime behavior, order placement, sizing, promotion validation, or
  runtime mode authorization.
- Research artifacts remain `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Plan

1. Add a catalog reuse/check job path that returns the active catalog when it is
   already candidate-depth ready.
2. Make the top-level button use the reuse/check path by default.
3. Keep a clearly labeled explicit rebuild button for the long collection path.
4. Add focused operator UI regressions.
5. Run focused tests plus baseline validation.

## Acceptance Criteria

- The default catalog button does not queue a full rebuild when an active
  candidate-depth catalog exists.
- Operators can still explicitly request a full rebuild.
- UI copy distinguishes checking/reusing from rebuilding.
- Focused operator UI tests and baseline contracts pass.

## Outcome

- Stopped the accidental local server process that was running the catalog
  rebuild and removed only the partial rebuild output directory for
  `refresh-historical-data-catalog-803b557310a7403694fd926dfcbfb082`.
- Marked the stale accidental job row as failed with
  `operator_cancelled_accidental_catalog_rebuild` so the UI does not keep
  reporting it as running.
- Added `check-historical-data-catalog` as the default job queued by the
  catalog endpoint when `force_rebuild` is absent or false.
- Kept the long rebuild path available only when the UI posts
  `force_rebuild: true`.
- Updated the Research tab labels and milestone copy so the default action is
  check/reuse, with rebuild called out as explicit and long-running.
- Updated operator UI tests for the new default job semantics and progress
  wording.

## Validation

- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - 441 passed
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
  - 83 passed
