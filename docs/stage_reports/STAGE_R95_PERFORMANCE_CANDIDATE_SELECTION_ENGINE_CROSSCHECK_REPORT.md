# Stage R95 Performance Candidate Selection Engine Crosscheck Report

Date: 2026-05-12
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR95-01-performance-candidate-selection-engine-crosscheck.md`

## Decision

WPR95-01 is complete. The research branch now exposes candidate-selection
performance evidence for historical-cycle runs without claiming live readiness
or unimplemented GPU acceleration.

## Scope Completed

- Added exact explicit-grid brute-force-equivalent accounting through
  `SearchSpace.grid_size()`.
- Added `compute` policy parsing to historical research-cycle specs:
  bounded CPU threads, NVIDIA/CUDA preference mode, device class, and
  `gpu_required` metadata.
- Added a research-only candidate-selection performance plan to cycle
  artifacts, including materialized search count, sampled fraction, raw sampled
  fraction, brute-force avoidance ratio, stability-region policy, and compute
  policy.
- Parallelized aggregate candidate backtests with a bounded thread pool while
  preserving candidate order for rankings and evidence tables.
- Configured checked-in full-cycle research specs to use `cpu_threads: 15` and
  prefer NVIDIA 50-series CUDA only when a validated backend exists.
- Recorded the absent CUDA backend as `ISSUE-R95-001` in
  `docs/KNOWN_ISSUES.md`.

## Boundary Notes

No live config, order placement, promotion readiness, runtime mode, or sizing
logic was changed. Outputs remain `research_only: true`, `observe_only: true`,
and `promotion_ready: false`. The new performance plan explicitly states that
GPU acceleration is blocked until a concrete CUDA backend writes backend
evidence.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\optimization -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_synthetic.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
python -c "import json, pathlib; [json.load(open(path, encoding='utf-8')) for path in pathlib.Path('configs/research').glob('*.json')]; print('configs ok')"
git diff --check
```

Observed counts:

- `tests/optimization`: 20 passed
- `tests/contracts/test_research_cycle_contract.py`: 35 passed
- `tests/historical/test_full_cycle_synthetic.py`: 13 passed
- `tests/contracts`: 401 passed
- `tests/research_discovery`: 152 passed

## Open Follow-Up

`ISSUE-R95-001` remains open: no CUDA/GPU backtest backend is registered. The
current engine can record GPU preference truthfully and use CPU aggregate
parallelism, but NVIDIA speedup claims require a later validated backend with
reference parity evidence.
