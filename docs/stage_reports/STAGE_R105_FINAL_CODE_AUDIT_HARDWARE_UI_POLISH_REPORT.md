# Stage R105 Final Code Audit Hardware UI Polish Report

Date: 2026-05-19
Packet: `docs/work_packets/WPR105-101-final-code-audit-hardware-ui-polish.md`

## Scope

Final audit and polish for the hardware-utilization benchmark, CLI, operator
service, artifact index, and Research tab wiring. This is diagnostic-only
research readiness work and does not alter candidate gates, backtest semantics,
live execution, runtime mode, order placement, live configuration, promotion
behavior, or sizing behavior.

## Changes

- Skipped ASGI app construction when Windows process-pool workers import the
  CLI module as `__mp_main__`.
- Centralized hardware benchmark guardrails for bounded CPU/GPU probe seconds,
  matrix size, and explicit worker counts.
- Changed prolonged-study CPU readiness to require worker-capacity saturation;
  logical-capacity saturation remains a separate oversubscription diagnostic.
- Freed CuPy memory pools best-effort on GPU probe failures.
- Reworked Research UI status text so worker-capacity and logical-capacity
  saturation are displayed separately.
- Added route tests for invalid hardware benchmark payloads.
- Replaced repeated broad artifact-index `rglob` scans with one pruned manifest
  walk that skips trial artifacts, snapshots, raw data, caches, and generated
  backtest subtrees.

## Validation

- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_cycle\test_hardware_utilization_benchmark.py tests\tradingbotsuite\test_operator_ui.py::test_operator_research_page_keeps_hmm_knn_monitoring_observe_only tests\tradingbotsuite\test_operator_ui.py::test_operator_research_job_routes_default_to_r104_deep_and_exact_specs tests\tradingbotsuite\test_operator_ui.py::test_operator_hardware_utilization_route_rejects_invalid_payloads tests\tradingbotsuite\test_operator_ui.py::test_operator_research_artifacts_survives_corrupt_json tests\tradingbotsuite\test_operator_ui.py::test_operator_research_artifacts_include_hardware_utilization_summary tests\tradingbotsuite\test_operator_ui.py::test_operator_hardware_utilization_job_queues_completes_and_lists_artifact -q`
  - `16 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `427 passed`
- `$env:PYTHONPATH='src'; python -m pytest -q`
  - `1388 passed, 1 skipped`
- `git diff --check`
  - Passed with CRLF warnings only.
- Hardware audit benchmark:
  - CPU worker-capacity utilization: `93.453006%`
  - CPU logical-capacity utilization: `46.726503%`
  - GPU status: `cupy_matrix_probe_executed`
  - Report:
    `data/research/operator_runs/r105/hardware_utilization_audit/hardware_utilization_report.json`
- Artifact index timing on current local tree:
  - `OperatorConsoleService.list_artifacts()` returned 102 items in about
    `3.13` seconds after pruning.
- Browser smoke:
  - Desktop and mobile Playwright checks confirmed the Research tab exposes the
    hardware benchmark controls, hardware board tile, worker/logical CPU status,
    artifact visibility, and no live/promotion UI controls.

## Boundary

All outputs remain `research_only`, `observe_only`, `promotion_ready: false`,
`candidate_acceptance_allowed: false`, and `speed_claimed: false`.
