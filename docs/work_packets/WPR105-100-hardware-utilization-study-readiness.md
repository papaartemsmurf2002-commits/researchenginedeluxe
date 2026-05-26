# WPR105-100 Hardware Utilization Study Readiness

Owner: Codex Research Agent
Stage: R105 candidate factory component falsification
Status: closed
Created: 2026-05-19

## Goal

Add a research-only hardware utilization benchmark and operator surface for
prolonged-study readiness. The benchmark must measure local CPU process-pool
saturation, optional CuPy/CUDA availability and GPU matrix throughput, and
produce truthful recommendations for when CPU workers, vectorized CPU paths, or
CUDA paths should be used.

## Allowed paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/contracts/**`
- `docs/work_packets/**`
- `docs/stage_reports/**`
- `src/tradingbotsuite/**`
- `tests/**`

## Constraints

- Preserve the research boundary: no live execution, no order placement, no
  runtime-mode mutation, no live configuration writes, no promotion behavior,
  and no sizing behavior.
- Do not mark research artifacts `promotion_ready: true`.
- Do not close `ISSUE-R104-001` unless expanded durable BTC/ETH primary-bar
  fixtures and rerun evidence actually exist.
- Treat CPU/GPU utilization as local diagnostic evidence. Do not claim
  profitability, production speedup, live readiness, or candidate readiness.
- A 100 percent target is valid only for bounded CPU/GPU saturation probes; it
  must not hide I/O, artifact-write, scheduler, data-size, or GIL bottlenecks.

## Planned implementation

- Add a `benchmark-hardware-utilization` CLI command guarded as a research
  command and output-root allowlisted.
- Add a reusable benchmark module that writes a JSON manifest with CPU worker
  capacity, logical CPU capacity, CuPy/CUDA runtime evidence, GPU throughput
  evidence when available, and recommendation metadata.
- Wire the operator service, API route, artifact index, and Research tab so the
  benchmark can be queued and inspected from the UI.
- Add focused unit, live-boundary, CLI, and operator UI tests.

## Planned validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_cycle\test_hardware_utilization_benchmark.py tests\live\test_preflight.py tests\contracts\test_research_cycle_contract.py tests\tradingbotsuite\test_operator_ui.py -q
$env:PYTHONPATH='src'; python -m tradingbotsuite.main benchmark-hardware-utilization --output-dir operator_runs\r105\hardware_utilization --cpu-seconds 3 --gpu-seconds 3 --matrix-size 2048
git diff --check
```

## Exit evidence

- Added `benchmark-hardware-utilization` as a centralized research command,
  live-rejected through the command registry and output-root allowlisted
  through the shared direct CLI resolver.
- Added `hardware-utilization-study-readiness-v1` reports with research-only
  boundary metadata, CPU process-pool saturation evidence, physical/logical CPU
  count diagnostics, optional CuPy/CUDA matrix-throughput evidence,
  oversubscription warnings, and backend recommendations.
- Wired the operator service, API route, artifact index, Research tab button,
  control panel, operator board tile, status grid, and artifact card for the
  hardware benchmark.
- Local hardware evidence:
  `python -m tradingbotsuite.main benchmark-hardware-utilization --output-dir operator_runs\r105\hardware_utilization --cpu-seconds 3 --gpu-seconds 3 --matrix-size 2048`
  wrote `data/research/operator_runs/r105/hardware_utilization/hardware_utilization_report.json`.
  The auto CPU worker path selected `8` detected physical workers on a
  `16` logical CPU machine and reached `90.414925%` worker-capacity
  utilization. The CuPy/CUDA probe executed on `NVIDIA GeForce RTX 5070 Ti`
  and recorded `23844.730073` approximate GFLOP/s for the diagnostic matrix
  workload.
- Crosscheck evidence:
  explicit `16` CPU workers stayed below the saturation target at
  `69.590749%`, so the chosen prolonged-study option is the auto physical-core
  process-pool path plus CUDA only for supported fixed-holding/diagnostic
  matrix workloads.
- Focused validation passed for the benchmark module, live rejection, boundary
  command registry, operator route, artifact indexing, UI page, and isolated
  hardware job execution. Full validation passed with `1379 passed, 1 skipped`.
  Discovery and historical benchmark gates also passed under
  `data/research/operator_runs/r105/hardware_final_crosscheck/**`.
