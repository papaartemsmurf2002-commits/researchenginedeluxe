# Work Packet: WPR106-66 Autopilot Forced Cycle Schema Handoff

## Goal

Fix the forced Research Autopilot failure where the historical-cycle helper
receives operator-only bookkeeping keys and rejects the strict
`historical_research_cycle` schema before compute starts.

## Current Repo Facts

- The latest forced run
  `run-research-autopilot-93c17f8f75b742ceba023cba6fea3c5b` failed quickly with
  `historical_research_cycle unknown schema keys: operator_job_id,
  operator_original_spec_path, operator_overwrite_protection`.
- The request correctly set `force_upstream_recompute: true`, so this is not a
  reused-evidence run. It is a schema handoff bug at the first upstream compute
  step.
- WPR106-65 made new compute a first-class UI action and added an invariant that
  forced requests cannot complete successfully without upstream execution.

## Allowed Edit Paths

- `docs/work_packets/WPR106-66-*.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `README.md`
- `docs/RESEARCH_BRANCH_DISTILLATION.md`
- `src/tradingbotsuite/operator_console.py`
- `tests/tradingbotsuite/test_operator_ui.py`

## Research Boundary

- Do not start historical catalog rebuilds, historical cycles, exact discovery,
  or other long research compute during this fix packet.
- Do not rewrite generated research artifacts.
- Do not weaken historical-cycle schema validation.
- Do not change strategies, candidate gates, backtest math, live execution,
  sizing, runtime mode, or promotion behavior.
- Autopilot outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Plan

1. Inspect the failed manifest and generated cycle spec handoff.
2. Trace where `operator_*` keys are injected into cycle specs.
3. Move operator metadata out of the strict cycle spec payload or strip it
   before validation while preserving audit metadata in the job result.
4. Add regressions proving forced autopilot cycle handoff uses schema-clean
   specs.
5. Run focused operator tests, compile, contracts, bridge tests, and full suite.

## Acceptance Criteria

- Forced autopilot no longer injects unknown `operator_*` keys into
  `historical_research_cycle` specs.
- Historical-cycle schema validation remains strict.
- A forced autopilot request reaches the cycle helper with a clean spec and can
  proceed to exact discovery in tests.
- Validation passes.

## Diagnosis

The forced autopilot request was correct. It set
`force_upstream_recompute: true` and reached the BTC historical-cycle helper.
The failure happened before compute because `_run_isolated_historical_research_cycle`
created an isolated `cycle_spec.json` and inserted:

- `operator_job_id`
- `operator_original_spec_path`
- `operator_overwrite_protection`

Those keys are accepted by discovery specs, but not by strict
`historical_research_cycle` specs. The cycle parser rejected the isolated spec
before any upstream compute could start.

## Implementation Notes

- Kept `cycle_spec.json` schema-clean for historical-cycle execution.
- Moved operator bookkeeping into `operator_metadata.json` next to the isolated
  spec.
- Returned `operator_metadata_path` in the historical-cycle job result for audit
  visibility.
- Added assertions that manual isolated historical-cycle handoff and forced
  autopilot historical-cycle handoff do not put `operator_*` keys in the cycle
  spec payload.
- Historical-cycle schema validation remains strict; no accepted schema keys
  were added.

## Validation

- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_historical_cycle_job_writes_isolated_output tests\tradingbotsuite\test_operator_ui.py::test_operator_research_autopilot_force_upstream_recompute_runs_isolated_prerequisites -q`
  passed: 2 passed.
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
  passed: 90 passed.
- `python -m compileall -q src\tradingbotsuite` passed.
- `PYTHONPATH=src python -m pytest tests\contracts -q` passed: 441 passed.
- `PYTHONPATH=src python -m pytest tests\research_discovery\test_candidate_pack_bridge.py -q`
  passed: 37 passed.
- `PYTHONPATH=src python -m pytest tests -q` passed: 1569 passed, 1 skipped,
  1 known XGBoost device warning.

## Outcome

WPR106-66 is complete. No catalog rebuild, historical cycle, exact discovery,
generated research artifact rewrite, live/paper runtime change, order/sizing
change, candidate-pack write, or promotion claim was made by this packet. The
next forced autopilot run should pass the historical-cycle schema handoff
instead of failing on `operator_*` keys.
