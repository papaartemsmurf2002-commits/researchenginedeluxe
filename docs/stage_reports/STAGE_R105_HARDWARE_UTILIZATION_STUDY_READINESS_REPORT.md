# Stage R105 Hardware Utilization Study Readiness Report

Date: 2026-05-19
Owner: Codex Research Agent
Stage: R105 candidate factory component falsification
Status: complete; candidate-ready evidence still blocked by ISSUE-R104-001

## Research Boundary

This packet added a diagnostic benchmark and operator surface only. It did not
place orders, change runtime mode, write live configuration, touch sizing,
promote a candidate, or mark any research artifact `promotion_ready: true`.

## External Guidance Used

- Python documentation says CPython threads are limited by the GIL for
  CPU-bound Python bytecode and recommends `multiprocessing` or
  `concurrent.futures.ProcessPoolExecutor` for better multi-core use.
- Python `ProcessPoolExecutor` documentation states it uses `multiprocessing`
  to side-step the GIL, with the usual pickling and importability constraints.
- scikit-learn parallelism documentation warns against oversubscription when
  joblib, OpenMP, and BLAS/LAPACK threads multiply beyond CPU capacity.
- CuPy 14 documentation lists CUDA 12.x and 13.x PyPI wheel families and
  keeps CUDA Toolkit/library setup explicit.

## Implementation

- Added `src/tradingbotsuite/research_cycle/hardware_benchmark.py`.
- Added CLI command `benchmark-hardware-utilization` with output-root
  allowlisting and live rejection through the research command registry.
- Added operator route/job execution under
  `operator_runs/hardware_utilization/<job_id>`.
- Added Research tab controls, status grid rows, operator-board hardware tile,
  artifact-index support, and artifact-card rendering.
- Added focused tests for benchmark payloads, CLI plumbing, live-boundary
  registry, operator route queuing, artifact indexing, page wiring, and job
  execution.

## Local Hardware Evidence

Primary command:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main benchmark-hardware-utilization --output-dir operator_runs\r105\hardware_utilization --cpu-seconds 3 --gpu-seconds 3 --matrix-size 2048
```

Result:

- Report:
  `data/research/operator_runs/r105/hardware_utilization/hardware_utilization_report.json`
- CPU probe: passed
- Auto CPU workers: `8`
- Detected logical CPUs: `16`
- Detected physical cores: `8`
- CPU worker-capacity utilization: `90.414925%`
- CPU logical-capacity utilization: `45.207463%`
- GPU probe: passed
- GPU: `NVIDIA GeForce RTX 5070 Ti`
- GPU execution status: `cupy_matrix_probe_executed`
- Diagnostic matrix throughput: `23844.730073` approximate GFLOP/s
- Recommended best option:
  `hybrid_process_pool_cpu_plus_cuda_supported_fixed_holding`

Comparison command:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main benchmark-hardware-utilization --output-dir operator_runs\r105\hardware_utilization_cpu16 --cpu-workers 16 --cpu-seconds 3 --gpu-seconds 1 --matrix-size 1024
```

Result:

- Explicit logical-worker run reached `69.590749%` worker/logical capacity.
- The selected local prolonged-study option is therefore the auto
  physical-core process-pool CPU path for pure Python CPU-bound work, plus
  CUDA only for fixed-holding or diagnostic matrix workloads where the branch
  has parity constraints.

## UI Wiring

The Research tab now exposes:

- Hardware Readiness function block.
- Hardware Utilization Benchmark control panel.
- Queue action for `POST /api/operator/research/jobs/benchmark-hardware-utilization`.
- Operator-board hardware status tile.
- Research status rows for selected option, CPU logical percentage, and GPU
  probe state.
- `hardware_utilization` artifact card.

## Validation

Focused validation passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_cycle\test_hardware_utilization_benchmark.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py::test_historical_research_cycle_is_registered_as_research_command tests\live\test_preflight.py::test_live_preflight_rejects_research_command_even_when_other_live_checks_pass -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py::test_boundary_contract_lists_research_command_registry tests\live\test_cli_boundary.py::test_direct_research_cli_output_dir_values_use_shared_resolver -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_research_page_keeps_hmm_knn_monitoring_observe_only tests\tradingbotsuite\test_operator_ui.py::test_operator_research_job_routes_default_to_r104_deep_and_exact_specs tests\tradingbotsuite\test_operator_ui.py::test_operator_research_artifacts_include_hardware_utilization_summary tests\tradingbotsuite\test_operator_ui.py::test_operator_hardware_utilization_job_queues_completes_and_lists_artifact tests\tradingbotsuite\test_operator_ui.py::test_operator_research_job_blocked_in_live_mode_without_position -q
$env:PYTHONPATH='src'; python -m tradingbotsuite.main benchmark-hardware-utilization --output-dir operator_runs\r105\hardware_utilization --cpu-seconds 3 --gpu-seconds 3 --matrix-size 2048
$env:PYTHONPATH='src'; python -m tradingbotsuite.main benchmark-hardware-utilization --output-dir operator_runs\r105\hardware_utilization_cpu16 --cpu-workers 16 --cpu-seconds 3 --gpu-seconds 1 --matrix-size 1024
git diff --check
```

`git diff --check` passed with CRLF normalization warnings only.

Full validation passed after implementation:

```powershell
$env:PYTHONPATH='src'; python -m pytest -q
```

Result: `1379 passed, 1 skipped`.

Performance crosscheck gates also passed:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main benchmark-discovery-run --tier quick --repeat 2 --output-dir operator_runs\r105\hardware_final_crosscheck\discovery_quick
$env:PYTHONPATH='src'; python -m tradingbotsuite.main benchmark-historical-research-cycle --tier small --repeat 2 --output-dir operator_runs\r105\hardware_final_crosscheck\historical_small
```

- Discovery benchmark: gate passed, evidence complete, mean completed trials
  `3.0`, mean full elapsed seconds `0.203576`, mean resumed elapsed seconds
  `0.151846`.
- Historical benchmark: gate passed, evidence complete, mean elapsed seconds
  `3.00114`, mean rows/second `593.298534`, mean candidate
  backtests/minute `381.048073`, mean feature rows/second `1310.064403`.

## Issue State

`ISSUE-R104-001` remains open. Expanded durable BTC/ETH primary-bar fixtures
and reruns are still required before candidate-ready claims.
