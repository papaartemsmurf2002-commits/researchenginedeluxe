# WPR105-101 Final Code Audit Hardware UI Polish

Owner: Codex Research Agent
Stage: R105 candidate factory component falsification
Status: closed
Created: 2026-05-19

## Goal

Audit the hardware-utilization benchmark, CLI, operator route, artifact index,
and Research tab for confusing status text, brittle input handling, and
research-boundary drift. Patch narrow issues found during the audit.

## Allowed paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/**`
- `docs/stage_reports/**`
- `src/tradingbotsuite/**`
- `tests/**`

## Constraints

- Preserve the research boundary: no live execution, order placement, runtime
  mode mutation, live configuration writes, promotion behavior, or sizing
  behavior.
- Do not mark research artifacts `promotion_ready: true`.
- Keep this packet to audit polish only; do not change candidate gates,
  backtest semantics, or discovery scoring.

## Planned validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_cycle\test_hardware_utilization_benchmark.py tests\tradingbotsuite\test_operator_ui.py::test_operator_research_page_keeps_hmm_knn_monitoring_observe_only tests\tradingbotsuite\test_operator_ui.py::test_operator_research_artifacts_include_hardware_utilization_summary tests\tradingbotsuite\test_operator_ui.py::test_operator_hardware_utilization_job_queues_completes_and_lists_artifact -q
git diff --check
```

## Audit findings

- Windows `ProcessPoolExecutor` workers import the CLI module as `__mp_main__`;
  ASGI app construction is now skipped there to avoid benchmark pollution.
- Hardware benchmark inputs now fail closed before output-directory creation
  when CPU/GPU probe durations or GPU matrix sizes are outside bounded UI/CLI
  limits.
- CPU readiness now uses worker-capacity saturation as the selected target.
  Logical-capacity saturation remains a separate oversubscription diagnostic.
- CuPy probe failure paths now release CuPy memory pools best-effort before
  returning fallback evidence.
- Research artifact indexing now uses a single pruned manifest scan instead of
  repeated broad recursive scans through trial artifacts, snapshots, raw data,
  and caches.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_cycle\test_hardware_utilization_benchmark.py tests\tradingbotsuite\test_operator_ui.py::test_operator_research_page_keeps_hmm_knn_monitoring_observe_only tests\tradingbotsuite\test_operator_ui.py::test_operator_research_job_routes_default_to_r104_deep_and_exact_specs tests\tradingbotsuite\test_operator_ui.py::test_operator_hardware_utilization_route_rejects_invalid_payloads tests\tradingbotsuite\test_operator_ui.py::test_operator_research_artifacts_survives_corrupt_json tests\tradingbotsuite\test_operator_ui.py::test_operator_research_artifacts_include_hardware_utilization_summary tests\tradingbotsuite\test_operator_ui.py::test_operator_hardware_utilization_job_queues_completes_and_lists_artifact -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest -q
$env:PYTHONPATH='src'; python -m tradingbotsuite.main benchmark-hardware-utilization --output-dir operator_runs\r105\hardware_utilization_audit --cpu-seconds 1 --gpu-seconds 1 --matrix-size 1024
git diff --check
```

Results:

- Focused audit tests: `16 passed`.
- Contract baseline: `427 passed`.
- Full suite: `1388 passed, 1 skipped`.
- Local audit benchmark: CPU worker-capacity utilization `93.453006%`,
  logical-capacity utilization `46.726503%`, GPU status
  `cupy_matrix_probe_executed`.
- Invalid CLI probe input now exits before creating
  `data/research/operator_runs/r105/hardware_invalid_probe`.
- Browser smoke on `http://127.0.0.1:8001/ui/research` showed the Hardware
  board tile, artifact list, and mobile viewport status text.
