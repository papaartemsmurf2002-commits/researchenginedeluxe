# Agent name

KNN Agent

# Task received

Benchmark CPU vs CuPy Lorentzian distance on synthetic and real matrix sizes.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/source_inputs/tradingbotsuite_critical_audit_orchestrator_next_agent.md`
- `docs/tradingbotsuite_runtime/source_inputs/orchestrator_btc_eth_perps_architecture_review_v3.md`
- `src/tradingbotsuite/research/hmm_knn.py`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `data/research/v2-btc-research-1/btcusdt_dataset.parquet`
- Temporary benchmark output: `C:\Users\papaa\AppData\Local\Temp\tbs_lorentzian_bench_results.json`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_lorentzian_cpu_cupy_benchmark.md`

# Commands/tests run

Protocol and implementation lookup:

```powershell
Get-Content -Path docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_PROMPTS.md -TotalCount 240
Get-Content -Path docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_ISSUES.md -TotalCount 160
rg -n "def lorentzian_distance_matrix|lorentzian_distance_matrix|cupy|CuPy|cuda|gpu" src tests docs\tradingbotsuite_runtime configs
```

Result:

```text
HMM_MULTI_KNN_AGENT_ISSUES.md reported no open issues.
Current CPU implementation is src/tradingbotsuite/research/hmm_knn.py::lorentzian_distance_matrix.
It computes np.log1p(abs(query[:, None, :] - train[None, :, :]) / scales).sum(axis=2).
```

Environment probe:

```powershell
$env:PYTHONPATH='src'; python <probe for Python, CuPy, CPU, and GPU>
py -0p
Get-CimInstance Win32_Processor
Get-CimInstance Win32_VideoController
```

Result:

```text
Active repo Python: 3.14.0
Active repo Python CuPy: not installed
Available Python runtimes: 3.14 and 3.11
CPU: AMD Ryzen 7 7700 8-Core Processor, 8 cores / 16 logical processors
GPU: NVIDIA GeForce RTX 5070 Ti
```

Real matrix extraction:

```powershell
$env:PYTHONPATH='src'; python <script using load_hmm_knn_plan, _prepare_dataset, _walk_forward_frames, robust_scaler_fit>
```

Result:

```text
matrix_dir: C:\Users\papaa\AppData\Local\Temp\tbs_lorentzian_bench_matrices
real_split_0: query (156, 28), train (703, 28)
real_split_1: query (156, 28), train (867, 28)
real_split_2: query (134, 28), train (1031, 28)
```

Temporary CuPy setup:

```powershell
$venv = Join-Path $env:TEMP 'tbs_cupy_bench_py311'
py -3.11 -m venv $venv
& (Join-Path $venv 'Scripts\python.exe') -m pip install --upgrade pip
& (Join-Path $venv 'Scripts\python.exe') -m pip install numpy cupy-cuda12x
& (Join-Path $venv 'Scripts\python.exe') -m pip install nvidia-cuda-runtime-cu12 nvidia-cuda-nvrtc-cu12
```

Reason:

```text
The active Python 3.14 environment had no CuPy.
The Python 3.11 temp venv could install cupy-cuda12x.
Initial CuPy probe saw the RTX 5070 Ti but failed on missing nvrtc*.dll; installing nvidia-cuda-runtime-cu12 and nvidia-cuda-nvrtc-cu12 fixed kernel execution.
```

Benchmark command:

```powershell
& "$env:TEMP\tbs_cupy_bench_py311\Scripts\python.exe" <benchmark script>
```

Benchmarked implementations:

```python
def cpu_lorentzian(q, t):
    return np.log1p(np.abs(q[:, None, :] - t[None, :, :])).sum(axis=2)

def gpu_lorentzian(qg, tg):
    return cp.log1p(cp.abs(qg[:, None, :] - tg[None, :, :])).sum(axis=2)
```

No pytest command was run because this was a performance benchmark and did not change production code or tests.

# Benchmark environment

```text
Python: 3.11.0 in temp venv
NumPy: 2.4.4
CuPy: 14.0.1
GPU: NVIDIA GeForce RTX 5070 Ti
GPU global memory reported by CuPy: 17.094 GB
CPU: AMD Ryzen 7 7700, 8 cores / 16 logical processors
```

Notes:

- CPU and CuPy both used float64.
- Timings exclude first warm-up call, so CuPy JIT warm-up is not included.
- `cupy_gpu_resident_ms` keeps query/train on GPU and measures distance computation.
- `cupy_end_to_end_ms` includes CPU-to-GPU upload and GPU-to-CPU distance-matrix copy-back, with CuPy's allocator cache active.
- Current KNN code consumes the full distance matrix on CPU for sorting, so `cupy_end_to_end_ms` is the more realistic lower-friction comparison unless KNN selection also moves to GPU.

# Results

| Case | Matrix | CPU NumPy median ms | CuPy resident median ms | CuPy end-to-end median ms | E2E speedup | Max abs error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| synthetic tiny | 64 x 256 x 28 | 3.9301 | 0.3783 | 0.5057 | 7.77x | 1.07e-14 |
| synthetic real split 0 size | 156 x 703 x 28 | 26.7333 | 2.7188 | 2.9454 | 9.08x | 1.42e-14 |
| synthetic real split 1 size | 156 x 867 x 28 | 32.9860 | 3.3270 | 3.7693 | 8.75x | 1.07e-14 |
| synthetic real split 2 size | 134 x 1031 x 28 | 35.0949 | 3.5788 | 3.9088 | 8.98x | 1.42e-14 |
| synthetic medium | 256 x 1024 x 28 | 69.1306 | 6.5791 | 6.8117 | 10.15x | 1.07e-14 |
| synthetic large | 512 x 2048 x 28 | 250.4712 | 26.4379 | 27.6759 | 9.05x | 1.07e-14 |
| real split 0 | 156 x 703 x 28 | 21.7110 | 2.8477 | 3.1817 | 6.82x | 7.11e-15 |
| real split 1 | 156 x 867 x 28 | 27.1073 | 3.4221 | 3.9663 | 6.83x | 7.11e-15 |
| real split 2 | 134 x 1031 x 28 | 27.0498 | 3.6335 | 3.9612 | 6.83x | 7.11e-15 |

Aggregate real-run distance timing:

```text
CPU NumPy median sum across three real splits: 75.8681 ms
CuPy resident median sum across three real splits: 9.9033 ms
CuPy end-to-end median sum across three real splits: 11.1092 ms
Real-size end-to-end speedup: about 6.83x
```

# Decisions made

- Used the repo's current broadcasted NumPy Lorentzian formula as the CPU baseline.
- Benchmarked synthetic random matrices with the same 28-feature width as the current BTC KNN feature set.
- Benchmarked actual real split matrices produced by the current HMM/KNN walk-forward preparation and train-only robust scaling.
- Used a temp Python 3.11 venv for CuPy instead of changing the active repo Python 3.14 environment.
- Installed CUDA runtime/NVRTC wheels only inside the temp venv after CuPy detected the GPU but could not compile kernels.

# Interpretation

CuPy is materially faster for the current broadcasted Lorentzian distance calculation:

```text
Real split speedup, end-to-end including transfer/copy-back: about 6.8x.
Synthetic speedup, end-to-end: about 7.8x to 10.1x.
GPU-resident compute speedup: about 7.4x to 10.5x.
Numerical agreement: max absolute error around 7e-15 to 1.4e-14.
```

The current real matrix sizes are still small. At these sizes, transfer overhead is not dominant because the broadcast/log/sum workload is large enough to benefit from GPU execution. The gain should become more important if the research dataset grows toward the critical-audit evidence floor, but the current full-distance-matrix approach will also become memory-bound.

For the current real artifact, CPU distance computation is not the main research blocker. The larger blockers remain low neighbor quality, sparse accepted trades, insufficient data volume, missing/neutralized context fields, and non-promotable BTC-only evidence. A CuPy distance path would improve research iteration speed, not model validity.

# Implementation notes for a future CuPy path

- Do not add CuPy as a default runtime dependency. Keep it optional under a research/GPU extra because normal runtime and live surfaces must not depend on GPU packages.
- The active Python 3.14 environment did not have CuPy. The working setup used Python 3.11 plus `cupy-cuda12x`, `nvidia-cuda-runtime-cu12`, and `nvidia-cuda-nvrtc-cu12`.
- If adding a repo-supported GPU path, expose it as a research-only backend such as `knn.distance_backend: "numpy" | "cupy" | "auto"`.
- Preserve exact deterministic output checks against NumPy for small matrices.
- Move neighbor selection/top-k to GPU if possible. Copying the full distance matrix back to CPU still worked well at current sizes, but it will become expensive as real history grows.
- Consider chunked GPU top-k instead of materializing `query x train x features` for very large runs.

# Assumptions

- The benchmark should compare the current exact Lorentzian broadcast formula, not an approximate nearest-neighbor algorithm.
- The real BTC split matrices under the current config are representative of the current research artifact dimensions.
- A temp venv is acceptable for benchmarking because it avoids modifying repo dependencies.
- Timing medians are more useful than single-run timings for this benchmark.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues before this task.

# Handoff notes for other agents

- CuPy can accelerate exact Lorentzian distance on this machine, but this is a research-speed improvement only.
- Do not use this benchmark to support any live-readiness claim.
- If implemented, keep GPU support optional, research-only, tested against NumPy, and reported in artifacts.
- The next performance experiment should benchmark GPU top-k selection and chunked distance computation at 10k+ event-row scale, because that is where full distance-matrix memory becomes the more important issue.
