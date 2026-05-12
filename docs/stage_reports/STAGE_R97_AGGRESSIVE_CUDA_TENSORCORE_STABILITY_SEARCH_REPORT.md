# Stage R97 Aggressive CUDA TensorCore Stability Search Report

Date: 2026-05-12
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR97-01-aggressive-cuda-tensorcore-stability-search.md`

## Summary

WPR97 extends the R96 GPU foundation with explicit, opt-in acceleration lanes:

- `cuda_batched_fixed_holding`: an exact RawKernel/CuPy fixed-holding backend for primary-bar research backtests.
- `cuda_screening_batch_v1`: a diagnostic matrix-screening evaluator for Tensor Core-style workloads, with CPU reference comparison and no candidate-gate authority.
- R97 stability counters and research-cycle routing fields that distinguish Tensor Core screening, exact GPU screening, CPU/reference validation, parity rechecks, and mismatches.

The existing `cuda_fixed_holding` backend remains intact as the R96 diagnostic backend.

## Research Boundary

All new artifacts remain research-only:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `diagnostic_only: true` for GPU/Tensor Core screening artifacts
- `position_sizing_input: false`, `live_signal_input: false`, and `order_placement_used: false` where new manifests/evidence are written

No live trading behavior, live config, order placement, promotion readiness, or sizing logic was changed.

## Implemented

- Added `cuda_batched_fixed_holding` backend support with lazy CuPy use, RawKernel scope, FP64 accounting, deterministic non-overlap trade construction, CPU/vector parity evidence, fallback reason codes, kernel hash, SM target, runtime evidence, and `speed_claimed: false`.
- Added backward-compatible compute fields:
  - `gpu_execution_profile`
  - `tensor_core_policy`
  - `gpu_batch_candidates`
  - `gpu_memory_fraction_limit`
  - `gpu_validation_sample_rate`
- Kept `auto` conservative: it remains CPU/vector unless GPU is requested and `gpu_execution_profile` is `cuda_exact_batched` or `hybrid_tensorcore_screening`.
- Added fail-closed `gpu_required` behavior when the requested GPU profile or runtime is unavailable.
- Added `cuda_screening_batch_v1` as a separate optimization evaluator, not a backtest backend. It can rank/prefilter diagnostic matrix workloads only and records CPU reference hashes, top-k overlap, score diffs, Tensor Core policy, and fallback reason.
- Extended stability-region counters:
  - `tensorcore_screened_count`
  - `gpu_exact_screened_count`
  - `cpu_reference_validated_count`
  - `parity_rechecked_count`
  - `mismatch_count`
  - retained R96 brute-force, GPU/CPU screened, validation, refinement, and avoidance counters.
- Added tests for backend contracts, fallback, manifest evidence, CUDA parity, conservative/opt-in routing, Tensor Core diagnostic boundaries, and stability counters.

## Hardware Evidence

Local CUDA evidence after implementation:

- GPU: NVIDIA GeForce RTX 5070 Ti
- Compute capability: 12.0
- Driver API version: 13020
- CUDA runtime version reported by CuPy: 12090
- CuPy: 14.0.1
- Memory total: 17094475776 bytes
- Runtime smoke test: passed

The focused hardware parity test passed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_cuda_batched_fixed_holding.py::test_cuda_batched_fixed_holding_matches_reference_when_runtime_available -q
```

Result: `1 passed`.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\backtesting tests\optimization tests\historical\test_research_cycle_benchmark.py tests\historical\test_full_cycle_synthetic.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_cuda_batched_fixed_holding.py::test_cuda_batched_fixed_holding_matches_reference_when_runtime_available -q
git diff --check
```

Observed results:

- `tests/contracts`: `413 passed`
- `tests/backtesting tests/optimization tests/historical/...`: `156 passed, 1 skipped`
- `tests/research_discovery`: `152 passed`
- focused CUDA hardware parity: `1 passed`

## Limitations

- No speedup is claimed. Batched CUDA manifests still write `speed_claimed: false`.
- Tensor Core screening is diagnostic/prefilter-only and cannot satisfy candidate gates, final trade accounting, event accounting, costs, or candidate acceptance.
- Strategy signal generation remains CPU/reference; GPU signal kernels are not introduced in this packet.
- Rich exits, lower-timeframe execution paths, true L2/depth, liquidation, and KNN acceptance remain CPU/reference or deferred.
- Candidate-ready/live-ready claims remain blocked by the existing comparator, no-regime baseline, exit-lab, validation-floor, stability, and candidate-pack evidence requirements.
