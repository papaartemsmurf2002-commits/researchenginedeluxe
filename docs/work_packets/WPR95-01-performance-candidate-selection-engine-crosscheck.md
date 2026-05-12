# WPR95-01 Performance Candidate Selection Engine Crosscheck

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Crosscheck and harden the research-cycle performance, candidate-selection, and
engine path so the branch can pursue stable candidate regions efficiently
without pretending to brute-force billions of combinations.

## Allowed Paths

- `configs/research/**`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/**`
- `docs/work_packets/**`
- `src/tradingbotsuite/optimization/**`
- `src/tradingbotsuite/research_cycle/**`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `tests/optimization/**`

## Scope

- Add explicit brute-force-equivalent search-space accounting.
- Add a research-cycle compute policy that can prefer NVIDIA/CUDA GPU when a
  real backend exists and otherwise use a bounded CPU-thread plan.
- Surface stability-region search policy and sampled-fraction evidence in
  candidate-space and trial-budget artifacts.
- Keep candidate selection research-only and fail closed for promotion/live
  interpretation.

## Non-Goals

- No live-ready candidate declaration, promotion readiness, live config writes,
  order placement, runtime-mode changes, or sizing logic.
- No unproven CUDA/GPU implementation claim.
- No exhaustive 8-billion-combination run.

## Validation Plan

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\optimization -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_synthetic.py -q
git diff --check
```

## Validation Result

Passed on 2026-05-12:

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

## Exit Evidence

- `SearchSpace.grid_size()` records exact explicit-grid brute-force-equivalent
  size without materializing the grid.
- Historical research-cycle specs now carry a bounded `compute` policy with
  CPU worker count and explicit NVIDIA/CUDA preference fields.
- Aggregate candidate backtests can run through a bounded thread pool while
  preserving deterministic candidate order in downstream artifacts.
- Candidate-space, trial-budget, and cycle manifests now expose a
  `candidate-selection-performance-plan-v1` payload with brute-force equivalent
  count, materialized count, sampled fraction, avoidance ratio, stability-region
  selection policy, CPU workers, and GPU truthfulness.
- Checked-in research-cycle configs now request `cpu_threads: 15` and prefer
  NVIDIA 50-series CUDA acceleration only when a validated backend exists.
- `ISSUE-R95-001` records the remaining CUDA backend gap as an open P1
  performance blocker instead of claiming GPU acceleration.
