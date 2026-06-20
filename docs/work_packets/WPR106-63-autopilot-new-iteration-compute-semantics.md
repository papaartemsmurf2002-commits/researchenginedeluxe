# Work Packet: WPR106-63 Autopilot New Iteration Compute Semantics

## Goal

Make Research Autopilot truthfully distinguish downstream eligibility refresh
from a new upstream compute iteration, and add an explicit operator path for
forcing upstream cycle/discovery/analysis recompute when the user wants to run
the next expensive local iteration.

## Current Repo Facts

- WPR106-57 through WPR106-62 are uncommitted local work and must be preserved.
- The latest autopilot run completed in about 80 seconds with
  `executed_step_count: 2` because it skipped catalog, BTC/ETH historical
  cycles, BTC/ETH exact discovery, analysis, deltas, and exit lab, then only
  executed BTC/ETH candidate eligibility.
- That run wrote new downstream eligibility evidence but did not run a new
  upstream research iteration.
- Existing autopilot status text currently reports any executed step as
  `executed_new_evidence`, which is too broad for operator decision-making.

## Allowed Edit Paths

- `docs/work_packets/WPR106-63-*.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_operator_ui.py`

## Research Boundary

- Do not start catalog rebuilds, historical cycles, discovery runs, or other
  long compute during this fix.
- Do not rewrite generated research artifacts.
- Do not change strategy math, candidate gates, order placement, sizing, live
  mode, or promotion behavior.
- Research outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Plan

1. Register the misleading autopilot completion semantics as a P1.
2. Add explicit autopilot compute-scope counters:
   upstream cycle/discovery/catalog recompute, downstream analysis/exit/eligibility,
   and skipped/reused prerequisites.
3. Change completion status details so downstream-only refresh is not reported
   as a new upstream iteration.
4. Add a `force_upstream_recompute` request flag for deliberate new iteration
   compute. When set, historical cycles, exact discovery, analysis, delta, exit
   lab, and eligibility should execute in isolated job output paths instead of
   skipping complete current artifacts.
5. Surface the flag and the compute-scope result in the Research UI.
6. Add operator regressions for downstream-only refresh and forced upstream
   recompute.
7. Run focused operator tests and baseline compile/contracts.

## Acceptance Criteria

- The latest run shape from the user is reported as downstream refresh on
  reused upstream evidence, not a completed new upstream iteration.
- A forced new iteration queues/runs upstream historical-cycle and exact
  discovery helper steps even when current artifacts already exist.
- Existing reuse mode remains available for readiness/eligibility refresh.
- UI request payload exposes the new forced-upstream intent.
- Tests and baseline validation pass.

## Implementation Notes

- Autopilot now classifies completed runs by compute scope:
  `reused_existing_evidence`, `refreshed_downstream_evidence`, or
  `executed_upstream_compute`.
- The exact posted shape where only BTC/ETH candidate eligibility executes is
  classified as downstream refresh with
  `new_iteration_compute_executed: false`.
- `force_upstream_recompute` is wired through the operator route and Research
  UI. Forced mode reuses a candidate-depth catalog when it is already ready,
  then reruns isolated historical-cycle, exact-discovery, analysis, delta,
  frozen-entry exit-lab, and optional eligibility helpers.
- Forced exact discovery bypasses stable-run reuse and writes isolated job
  outputs rather than overwriting stable completed discovery artifacts.
- Forced eligibility filters multiple-testing and validation-floor manifests to
  the fresh discovery artifact. If matching gate manifests do not exist, the
  eligibility helper records missing gate manifests fail-closed instead of
  mixing old validation evidence into the new iteration.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
  - 89 passed
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - 441 passed
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_candidate_pack_bridge.py -q`
  - 37 passed
- `$env:PYTHONPATH='src'; python -m pytest tests -q`
  - 1568 passed, 1 skipped, 1 XGBoost device warning
