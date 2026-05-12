# Stage R97 Throughput Default And TensorCore Dependency Report

Date: 2026-05-12
Work packet: `docs/work_packets/WPR97-04-throughput-default-and-tensorcore-dependency.md`

## Summary

WPR97-04 changes the default historical-cycle `auto` route back to the fastest
exact path measured locally: CPU vector aggregate screening plus reference
validation. Explicit CUDA profiles remain available for parity and diagnostic
GPU evidence:

- `gpu_execution_profile: cuda_exact_batched`
- `gpu_execution_profile: hybrid_tensorcore_screening`
- explicit `backtest_backend: cuda_batched_fixed_holding`

This supersedes the WPR97-02 GPU-first default because local RTX 5070 Ti
benchmarks showed the current one-candidate, artifact-producing CUDA backend is
parity-correct but slower than vector CPU execution. The CUDA exact backend
still records `speed_claimed: false`.

## Local Runtime Findings

Hardware/runtime:

- GPU: NVIDIA GeForce RTX 5070 Ti
- Compute capability: 12.0
- CuPy: 14.0.1
- CUDA runtime reported by CuPy: 12090
- Driver reported by CuPy: 13020

Single-backtest warm median timings:

| Rows | Vector median ms | `cuda_batched_fixed_holding` median ms | Vector/CUDA ratio |
| ---: | ---: | ---: | ---: |
| 720 | 54.781 | 97.386 | 0.563 |
| 5,760 | 259.384 | 434.296 | 0.597 |
| 20,000 | 896.819 | 1,497.205 | 0.599 |
| 50,000 | 2,428.408 | 4,251.721 | 0.571 |

Post-change full-cycle benchmark:

| Rows | Mode | Median seconds | Aggregate backend | Validation backend |
| ---: | --- | ---: | --- | --- |
| 240 | default | 5.028 | `vector_fixed_holding` | `reference` |
| 240 | explicit CUDA | 6.087 | `cuda_batched_fixed_holding` | `reference` |
| 720 | default | 9.301 | `vector_fixed_holding` | `reference` |
| 720 | explicit CUDA | 9.421 | `cuda_batched_fixed_holding` | `reference` |

Interpretation: the current CUDA exact lane is underfilled. It launches a small
RawKernel over a single candidate's signals, transfers arrays back to host,
assembles trades and artifacts on CPU, and runs CPU parity/reference checks.
This is correct but does not create enough device-resident work to keep the GPU
busy or beat the vector backend.

## Tensor Core Finding

Before this packet, CuPy matmul failed locally because `cublasLt*.dll` was not
discoverable. Installing `nvidia-cublas-cu12` fixed that runtime dependency, so
the optional `research-gpu` extra now declares `nvidia-cublas-cu12>=12.8`.

Tensor Core-shaped matrix screening after the dependency fix:

| Features | Queries | Dims | GPU matmul event ms | CPU64/GPU event ratio | Top-k overlap vs CPU64 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 5,000 | 256 | 64 | 0.064 | 716.713 | 1.0 |
| 20,000 | 512 | 128 | 0.207 | 83.953 | 1.0 |

The repo-level `cuda_screening_batch_v1` remains slower end-to-end than CPU-only
screening because it intentionally computes CPU reference parity and copies GPU
scores back to host. That is acceptable for diagnostic parity evidence, but the
future fast path must keep screening, top-k, and plateau refinement on device
before host materialization.

## Behavior Changes

- Default `CycleComputeSpec.gpu_execution_profile` is now `conservative`.
- `backtest_backend: auto` with the default profile uses
  `vector_fixed_holding` for supported aggregate fixed-holding screening.
- `auto` validation paths use the reference engine with fallback reason
  `auto_validation_reference_required`.
- Explicit `cuda_exact_batched` and `hybrid_tensorcore_screening` behavior is
  unchanged.
- `research-gpu` now includes `nvidia-cublas-cu12>=12.8`.

All outputs remain research-only:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `speed_claimed: false` for CUDA exact backtests

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_synthetic.py tests\historical\test_full_cycle_local_fixture_pack.py -q
$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_cuda_batched_fixed_holding.py tests\optimization\test_gpu_screening.py -q
```

Additional local runtime checks:

- Longer single-backtest vector vs CUDA timings through 50,000 rows.
- Post-change full-cycle default vs explicit CUDA timings.
- Tensor Core-shaped CuPy matmul benchmark after installing cuBLAS.
- `cuda_screening_batch_v1` local smoke with `tensor_core_used: true`,
  `gpu_execution_status: cuda_screening_executed`, `parity_status: passed`,
  and mean top-k overlap `1.0`.

## Remaining Performance Direction

The next meaningful GPU speedup is not more one-candidate backtest calls. It is a
device-resident many-candidate evaluator:

1. Generate simple-family signals in GPU batches or pre-materialize signal
   columns once.
2. Evaluate hundreds/thousands of candidate parameter rows per kernel launch.
3. Keep trade/event summaries, top-k, and plateau filters on GPU.
4. Copy back compact region summaries only.
5. Run exact CUDA and CPU/reference validation only on shortlisted stable
   regions.

Tensor Cores should stay limited to matrix-heavy screening and never final trade
accounting, cost accounting, event counting, or candidate acceptance.
