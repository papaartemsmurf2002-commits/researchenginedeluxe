# WPR97-04 Throughput Default And TensorCore Dependency

Status: closed
Owner: Codex Research Agent
Stage: R97 aggressive CUDA/TensorCore stability search

## Goal

Make the default research-cycle execution route faster based on local benchmark
evidence, while preserving explicit CUDA/Tensor Core research paths and all
research-only boundaries.

Local R97 evidence shows `cuda_batched_fixed_holding` is parity-correct on the
RTX 5070 Ti but slower than the CPU vector backend for the current
artifact-producing fixed-holding workload. Tensor Core-shaped matrix screening
also required the cuBLASLt runtime DLLs before CuPy matmul could execute.

## Allowed Paths

- `pyproject.toml`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/**`
- `docs/work_packets/**`
- `src/tradingbotsuite/research_cycle/**`
- `tests/contracts/**`
- `tests/historical/**`

## Non-Goals

- Do not alter live trading behavior, live config, order placement, promotion
  readiness, or sizing logic.
- Do not make CUDA or Tensor Core outputs promotion evidence.
- Do not remove explicit `cuda_batched_fixed_holding` or
  `hybrid_tensorcore_screening` support.
- Do not weaken CPU/reference parity, split, cost-stress, comparator, or
  validation-floor gates.

## Plan

1. Change default compute profile back to conservative vector/CPU routing for
   `backtest_backend: auto`.
2. Keep explicit `cuda_exact_batched` and `hybrid_tensorcore_screening` routing
   unchanged for users who request GPU evidence.
3. Add the missing cuBLAS runtime wheel to the optional `research-gpu` extra so
   Tensor Core-shaped CuPy matmul has the required DLLs.
4. Update tests and docs so the default is described as fastest exact routing,
   not GPU-first routing.
5. Rerun focused contracts, historical full-cycle checks, GPU parity tests, long
   local benchmarks, and diff checks.

## Exit Evidence

- Implemented default conservative `auto` routing for fastest measured exact
  aggregate screening.
- Preserved reference validation fallback under `auto`.
- Added `nvidia-cublas-cu12>=12.8` to the optional `research-gpu` dependency
  set after local Tensor Core-shaped CuPy matmul failed without cuBLASLt DLLs.
- Local RTX 5070 Ti benchmarks, Tensor Core smoke, focused tests, and validation
  evidence are recorded in
  `docs/stage_reports/STAGE_R97_THROUGHPUT_DEFAULT_AND_TENSORCORE_DEPENDENCY_REPORT.md`.
