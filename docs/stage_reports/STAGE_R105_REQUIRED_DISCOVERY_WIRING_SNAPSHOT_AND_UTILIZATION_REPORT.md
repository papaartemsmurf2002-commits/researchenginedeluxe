# Stage R105 Required Discovery Wiring Snapshot And Utilization Report

Date: 2026-05-20
Work packet: `docs/work_packets/WPR105-104-required-discovery-wiring-snapshot-and-utilization.md`
Status: closed

## Summary

WPR105-104 fixes the operator-console truthfulness gap around the required
R104/R105 evidence checklist. The checked BTCUSDT/ETHUSDT durable public-archive
fixture packs are still valid integrity-checked screening inputs, but the UI
and API now block them from being counted as candidate-depth-ready evidence.

Exact discovery remains the required long compute path, but it now queues into a
stable run-id output directory by default, auto-resumes an incomplete run state,
and exposes progress, rate, ETA, output directory, run_state, and latest snapshot
to the operator progress API and Research UI.

## Implementation Notes

- `r104_readiness_diagnostics()` now reports `fixture_integrity_ready`,
  `evidence_depth_ready`, `candidate_evidence_ready`, explicit row counts,
  effective coverage hours, and blocker codes against a one-year candidate
  evidence floor.
- Required progress no longer completes from stale or minimal artifacts. Current
  exact discovery completion requires the exact run IDs, completed state,
  570240 planned/completed trials, exhaustive search-space metadata, required
  outputs, and research-only/observe-only/non-promotion boundaries.
- The discovery job route marks exact durable sweeps as `stable_run_id` jobs.
  The isolated operator spec records requested/effective resume behavior and
  exact sweeps resume the stable run directory when a previous incomplete
  `run_state.json` exists.
- Discovery execution specs now support `executor: thread|process`. BTC/ETH
  exact durable sweep configs use `executor: process`; the runner initializes
  per-process real-discovery context and records the observed executor in the
  manifest and telemetry.
- The Research UI keeps feedback next to the required action buttons, renders
  an active discovery progress bar with ETA, labels compact data as
  `screening-only`, and restricts required charts/artifact selection to the
  current deep cycle and exact discovery IDs.

## Boundary

No live execution, order placement, runtime-mode mutation, live configuration
write, promotion behavior, candidate-pack write, or sizing behavior was added.
All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_spec.py tests\research_discovery\test_discovery_runner.py::test_discovery_runner_process_executor_smoke tests\tradingbotsuite\test_operator_ui.py::test_operator_research_progress_api_reports_r104_milestones tests\tradingbotsuite\test_operator_ui.py::test_operator_research_progress_api_indexes_bounded_r104_disk_artifacts tests\tradingbotsuite\test_operator_ui.py::test_operator_r104_readiness_api_reports_durable_btc_eth tests\tradingbotsuite\test_operator_ui.py::test_operator_research_job_routes_default_to_r104_deep_and_exact_specs tests\tradingbotsuite\test_operator_ui.py::test_operator_discovery_job_writes_research_only_artifacts tests\tradingbotsuite\test_operator_ui.py::test_operator_discovery_job_can_pause_and_resume -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts tests\research_discovery tests\tradingbotsuite\test_operator_ui.py -q
$env:PYTHONPATH='src'; python -m pytest -q
git diff --check
```

Result: compile passed; focused tests passed; scoped contracts/research/operator
suite passed with `654 passed`; full pytest passed with `1389 passed, 1
skipped`; `git diff --check` passed. Browser smoke covered desktop and 390px
mobile Research UI, no console errors, no mobile horizontal overflow, and the
server was stopped after verification.

## Remaining Blocker

`ISSUE-R104-001` remains open. Expanded BTCUSDT/ETHUSDT durable historical data
is still required before exact discovery or historical-cycle artifacts can be
treated as candidate-ready evidence.
