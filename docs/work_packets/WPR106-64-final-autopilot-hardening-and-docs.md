# Work Packet: WPR106-64 Final Autopilot Hardening And Docs

## Goal

Run a final scoped sweep over Research Autopilot after WPR106-63 so operator
results cannot again imply the wrong compute scope, blocked/failed runs remain
truthful, forced upstream recompute stays bounded and fail-closed, and the docs
explain how to use the feature without confusing reused evidence for a new
iteration.

## Current Repo Facts

- WPR106-63 resolved the eligibility-only status bug by adding explicit
  compute-scope status and `force_upstream_recompute`.
- The latest full validation before this packet passed with 1568 tests, 1
  skipped, and 1 XGBoost device warning.
- The worktree already contains uncommitted WPR106-57 through WPR106-63 local
  development changes. Preserve them and do not revert unrelated edits.

## Allowed Edit Paths

- `docs/work_packets/WPR106-64-*.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ACTIVE_INDEX.md`
- `README.md`
- `docs/RESEARCH_BRANCH_DISTILLATION.md`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_operator_ui.py`

## Research Boundary

- Do not start historical catalog rebuilds, historical cycles, exact discovery,
  or other long research compute during this hardening pass.
- Do not rewrite generated research artifacts.
- Do not change strategies, candidate gates, backtest math, live execution,
  sizing, runtime mode, or promotion behavior.
- Autopilot outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Audit Plan

1. Inspect autopilot status, failure, retry, step-limit, and forced recompute
   paths for ambiguous status or stale telemetry.
2. Harden blocked/failed manifests so they never remain `execution_status:
   running`.
3. Preserve truthful compute-scope fields on completed runs and expose the same
   status in job results, artifact summaries, and UI cards.
4. Add focused regressions for blocked and failed autopilot status details.
5. Update operator docs to describe reuse mode, downstream refresh, and forced
   upstream recompute.
6. Run focused operator tests, compile, contracts, and broader validation as
   needed.

## Acceptance Criteria

- Completed downstream-only, reused, and forced-upstream autopilot runs keep
  distinct statuses.
- Blocked and failed autopilot manifests are not left with
  `execution_status: running`.
- Operator-facing docs describe what the button does, when to force upstream
  recompute, and what does not happen automatically.
- Focused tests and baseline validation pass.

## Implementation Notes

- `operator_console.py` now lets terminal autopilot status win over computed
  scope in artifact summaries and writes terminal `execution_status` /
  `status_detail` for blocked and failed manifests.
- `operator.py` now accepts only real JSON booleans for autopilot boolean flags,
  so string values such as `"false"` cannot enable forced upstream recompute.
- Autopilot and catalog symbol parsing now rejects lists that trim down to no
  usable symbols.
- Operator-facing docs in `README.md`, `docs/ACTIVE_INDEX.md`,
  `docs/RESEARCH_BRANCH_DISTILLATION.md`, `docs/KNOWN_ISSUES.md`, and
  `docs/ORCHESTRATOR_STAGE_LEDGER.md` now describe compute-scope semantics and
  the research-only boundary.

## Validation

- First focused regression run caught the blank-symbol guard being applied to
  the catalog route but not autopilot; the route patch was corrected.
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_research_job_routes_default_to_r104_deep_and_exact_specs tests\tradingbotsuite\test_operator_ui.py::test_operator_research_autopilot_blocks_when_catalog_missing_without_refresh tests\tradingbotsuite\test_operator_ui.py::test_operator_research_autopilot_fails_after_retry_exhaustion -q`
  passed: 3 passed.
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
  passed: 89 passed.
- `python -m compileall -q src\tradingbotsuite` passed.
- `PYTHONPATH=src python -m pytest tests\contracts -q` passed: 441 passed.
- `PYTHONPATH=src python -m pytest tests\research_discovery\test_candidate_pack_bridge.py -q`
  passed: 37 passed.
- `PYTHONPATH=src python -m pytest tests -q` passed: 1568 passed, 1 skipped,
  1 known XGBoost device warning.

## Outcome

WPR106-64 is complete. No catalog rebuild, historical cycle, exact discovery,
generated research artifact rewrite, live/paper runtime change, order/sizing
change, candidate-pack write, or promotion claim was made.
