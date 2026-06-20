# Work Packet: WPR106-65 Autopilot New Compute Action

## Goal

Fix the operator workflow where clicking Research Autopilot can complete in a
few seconds by reusing existing artifacts even when the intended next step is a
new upstream compute iteration. The UI and service must make the difference
between evidence review and new compute impossible to miss.

## Current Repo Facts

- The latest local runs
  `run-research-autopilot-5b3667d3f0cb4e98b6ad170313c6799d` and
  `run-research-autopilot-ccd44aee842b4cb488656565c92e2998` completed in a few
  seconds because `force_upstream_recompute: false`, `executed_step_count: 0`,
  and all 13 steps were skipped as existing evidence.
- WPR106-63 and WPR106-64 made that status truthful, but the UI still exposes
  the default button as "Run Research Autopilot" with a separate unchecked
  force checkbox.
- The active research goal is to compute a new upstream cycle/discovery
  iteration before reviewing fresh evidence, while preserving research-only
  boundaries and candidate-pack gates.

## Allowed Edit Paths

- `docs/work_packets/WPR106-65-*.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ACTIVE_INDEX.md`
- `README.md`
- `docs/RESEARCH_BRANCH_DISTILLATION.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_operator_ui.py`

## Research Boundary

- Do not start historical catalog rebuilds, historical cycles, exact discovery,
  or other long research compute during this packet.
- Do not rewrite generated research artifacts.
- Do not change strategies, candidate gates, backtest math, live execution,
  sizing, runtime mode, or promotion behavior.
- Autopilot outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Plan

1. Make the UI provide an explicit "Run New Compute Iteration" action that
   sends `force_upstream_recompute: true`.
2. Keep a separate "Review Existing Evidence" action for fast cache/reuse
   review.
3. Add a service invariant so a forced upstream request cannot complete
   successfully if no upstream compute ran.
4. Add regressions for the UI action payload and the forced-compute invariant.
5. Run focused operator tests, compile, contracts, and broader validation as
   needed.

## Acceptance Criteria

- The primary operator action for new work sends `force_upstream_recompute:
  true`.
- A reuse-only review remains available but is visibly separate.
- Forced upstream autopilot completion with zero upstream execution is treated
  as blocked/failed evidence, not a successful run.
- Focused tests and baseline validation pass.

## Diagnosis

The latest user-triggered runs completed quickly because they were reuse
reviews, not compute iterations:

- `run-research-autopilot-5b3667d3f0cb4e98b6ad170313c6799d`
- `run-research-autopilot-ccd44aee842b4cb488656565c92e2998`

Both manifests recorded `force_upstream_recompute: false`,
`executed_step_count: 0`, `execution_status: reused_existing_evidence`, and 13
skipped steps. No cycle, discovery, analysis, delta, exit-lab, or eligibility
helper ran.

## Implementation Notes

- Replaced the ambiguous primary `Run Research Autopilot` UI action with
  explicit `Run New Compute Iteration` and `Review Existing Evidence` buttons.
- `Run New Compute Iteration` sends `force_upstream_recompute: true`.
- `Review Existing Evidence` sends `force_upstream_recompute: false`.
- The old force checkbox was removed from the required action so the operator
  cannot miss it.
- Added a service invariant: if `force_upstream_recompute` is true and the run
  reaches completion with zero upstream executed steps, autopilot writes a
  blocked manifest with
  `forced_upstream_recompute_requested_but_no_upstream_compute_executed`.
- Added regressions for the UI action payload and the forced-no-upstream
  invariant.

## Validation

- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_research_page_keeps_hmm_knn_monitoring_observe_only tests\tradingbotsuite\test_operator_ui.py::test_operator_research_job_routes_default_to_r104_deep_and_exact_specs tests\tradingbotsuite\test_operator_ui.py::test_operator_research_autopilot_reports_reused_existing_evidence_when_no_steps_execute tests\tradingbotsuite\test_operator_ui.py::test_operator_research_autopilot_force_upstream_recompute_runs_isolated_prerequisites tests\tradingbotsuite\test_operator_ui.py::test_operator_research_autopilot_forced_request_blocks_if_no_upstream_compute_runs -q`
  passed: 5 passed.
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
  passed: 90 passed.
- `python -m compileall -q src\tradingbotsuite` passed.
- `PYTHONPATH=src python -m pytest tests\contracts -q` passed: 441 passed.
- `PYTHONPATH=src python -m pytest tests\research_discovery\test_candidate_pack_bridge.py -q`
  passed: 37 passed.
- `PYTHONPATH=src python -m pytest tests -q` passed: 1569 passed, 1 skipped,
  1 known XGBoost device warning.

## Outcome

WPR106-65 is complete. No catalog rebuild, historical cycle, exact discovery,
generated research artifact rewrite, live/paper runtime change, order/sizing
change, candidate-pack write, or promotion claim was made by this packet. The
next operator compute run should use `Run New Compute Iteration`; a fast
`Review Existing Evidence` run is now clearly separate.
