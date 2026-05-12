# Stage R97 Default Accelerated Runtime Polish Report

Date: 2026-05-12
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR97-02-default-accelerated-runtime-polish.md`

## Summary

WPR97-02 makes the research-cycle accelerated path the default while keeping
CPU/vector/reference behavior as explicit fallback evidence.

Default historical-cycle behavior is now:

- `backtest_backend: auto`
- `compute.gpu_execution_profile: cuda_exact_batched`
- `compute.gpu_acceleration: prefer_nvidia_cuda_when_backend_available`

When the CUDA batched scope is supported and runtime evidence is available,
aggregate candidate screening uses `cuda_batched_fixed_holding`. When CUDA is
unavailable or a candidate is outside the GPU scope, the runner falls back to
vector/reference and records the reason. Split and cost-stress validation remain
CPU/reference when CUDA screening was requested.

## Boundary

No live trading behavior, live config, order placement, promotion readiness, or
sizing logic was changed. New and existing GPU artifacts remain research-only,
observe-only, non-promotion-ready, and non-speed-claiming.

## Math And Parity Crosscheck

Local CUDA runtime:

- GPU: NVIDIA GeForce RTX 5070 Ti
- Compute capability: 12.0
- CuPy: 14.0.1
- Driver API: 13020
- Runtime API reported by CuPy: 12090

Longer CUDA parity check used actual local CUDA/CuPy on five deterministic
720-row cases:

- trend default
- trend VWAP entry
- trend signal-close entry
- range reversion
- no-trade baseline

All cases passed exact signal-row agreement, strict trade/equity comparison
against CPU/vector references, zero max metric diff, and manifest
`parity_status: passed`.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\backtesting tests\optimization tests\historical\test_research_cycle_benchmark.py tests\historical\test_full_cycle_synthetic.py tests\historical\test_full_cycle_local_fixture_pack.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q
git diff --check
```

Observed results:

- `tests/contracts`: `413 passed`
- combined backtesting/optimization/historical command: `167 passed, 1 skipped`
- `tests/research_discovery`: `152 passed`
- `tests/live/test_preflight.py`: `32 passed`
- longer local CUDA parity script: 5/5 cases passed, max metric diff `0.0`

## Limitations

- No GPU speedup claim is made.
- Tensor Core screening remains diagnostic-only and cannot satisfy candidate
  gates or final accounting.
- CPU/reference validation remains mandatory for candidate advancement.
- Candidate-ready and live-ready claims remain blocked by the existing research
  evidence gates and the separate promotion/live process.
