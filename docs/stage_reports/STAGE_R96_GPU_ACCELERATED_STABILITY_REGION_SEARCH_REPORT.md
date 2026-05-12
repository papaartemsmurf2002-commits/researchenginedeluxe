# Stage R96 GPU Accelerated Stability Region Search Report

Date: 2026-05-12
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR96-01-cuda-fixed-holding-parity-and-stability-search.md`

## Summary

WPR96 added the first optional research-only CUDA path for candidate screening:
`cuda_fixed_holding`. The backend is intentionally limited to fixed-holding,
primary-bar backtests with the same support envelope as the CPU vector backend.
Signal generation, rich exits, lower-timeframe paths, KNN overlays, candidate
gates, and live-readiness decisions remain on existing CPU/reference paths.

The local environment now has the optional `research-gpu` dependency set
installed. Runtime evidence from `cuda_runtime_evidence()` reported one NVIDIA
GeForce RTX 5070 Ti device, compute capability `12.0`, CuPy `14.0.1`, CUDA
runtime `12090`, driver API `13020`, and runtime smoke status `passed`.

## Implemented

- Added `src/tradingbotsuite/backtesting/cuda_engine.py` with lazy CuPy import,
  stable support reason codes, runtime smoke coverage, diagnostic manifests, and
  `speed_claimed: false`.
- Added `cuda_fixed_holding` backend support to historical research-cycle specs
  and conservative `auto` routing.
- Kept `auto` CPU-safe: CUDA is used only when GPU is requested, the backend is
  selectable, runtime smoke passes, and the resolved backtest scope is eligible.
- Forced split and cost-stress validation scopes back to CPU/reference when CUDA
  routing is requested, so GPU screening cannot substitute for validation
  evidence.
- Added benchmark comparison evidence for serial CPU reference, 15-thread CPU
  reference, CPU vector, and optional CUDA runs.
- Added a stability-region search controller that screens/refines accepted
  regions without full-grid materialization and only reports observed backend
  counts from evaluator metadata.

## Boundaries

- Research outputs remain `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.
- No candidate pack is made promotion-ready.
- No live configuration, live runtime mode, order placement, or sizing behavior
  was changed.
- CUDA is a diagnostic screening backend, not a live-readiness shortcut.
- Rich exits, lower-timeframe execution, true L2/depth, liquidation features,
  Tensor Cores, FP4/FP8, and KNN acceleration remain deferred.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_vector_engine_matches_reference.py -q
$env:PYTHONPATH='src'; python -m pytest tests\optimization\test_stability_region_search_controller.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_synthetic.py -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_research_cycle_benchmark.py -q
$env:PYTHONPATH='src'; python -m pytest tests\optimization -q
$env:PYTHONPATH='src'; python -m pytest tests\backtesting -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q
git diff --check
```

Observed focused results:

- Backtesting focused parity: `31 passed, 1 skipped`
- Optimization stability search: `3 passed`
- Synthetic historical cycle: `15 passed, 1 skipped`
- Local fixture-pack historical cycle: `11 passed`
- Research-cycle benchmark: `12 passed`
- Contracts spec focused: `36 passed`
- Full contracts: `402 passed`
- Research discovery: `152 passed`
- Live preflight: `32 passed`
- Diff hygiene: `git diff --check` passed

## Residual Limits

- CUDA currently uses CuPy primitives plus a CPU trade loop; it is not a fused
  custom kernel implementation.
- CUDA performance is benchmarked as diagnostic evidence only. No general speedup
  claim is made.
- Hardware execution parity is naturally skipped where CUDA is unavailable, but
  fake-CuPy tests exercise the CUDA code path without a GPU.
- Candidate acceptance remains blocked by existing exit-lab, comparator,
  no-regime baseline, validation-floor, and stability evidence requirements.

## Decision

Stage R96 is complete. `ISSUE-R95-001` is resolved because a concrete optional
CUDA fixed-holding backend now exists with runtime evidence, parity tests,
fallback behavior, and benchmark reporting. The branch still does not claim
live-ready candidate selection or GPU speedup.
