# Agent name

KNN Agent

# Task received

Implement a research-only optional CuPy Lorentzian distance backend for regime-local KNN without making CuPy mandatory. Default must remain CPU, `auto` must fall back to CPU, tests must validate dispatch/fallback without GPU hardware, and live execution/operator/Hyperliquid/runtime controls must remain untouched.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `src/tradingbotsuite/research/hmm_knn.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_lorentzian_cpu_cupy_benchmark.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_distance_pool_sweep_diagnostics_audit.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_diagnostics_contract_hardening.md`

# Files changed

- `src/tradingbotsuite/research/hmm_knn.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_gpu_lorentzian_backend.md`

Note: the worktree also contained concurrent edits in adjacent research/runtime-readiness files, including `src/tradingbotsuite/main.py`, `src/tradingbotsuite/research/hmm_knn_experiments.py`, `src/tradingbotsuite/research/hmm_knn_monitoring.py`, `src/tradingbotsuite/research/live_readiness.py`, `tests/tradingbotsuite/test_live_readiness.py`, and new market-journal files. I did not revert or modify those unrelated changes.

# Commands/tests run

```powershell
Get-Content -Raw docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md
Get-Content -Raw docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md
Get-ChildItem docs/tradingbotsuite_runtime/agent_artifacts -Filter '*knn*' | Select-Object -ExpandProperty Name
Get-Content -Raw docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_lorentzian_cpu_cupy_benchmark.md
Get-Content -Raw docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_distance_pool_sweep_diagnostics_audit.md
Get-Content -Raw docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_diagnostics_contract_hardening.md
Get-Content -Raw src/tradingbotsuite/research/hmm_knn.py
Get-Content -Raw tests/tradingbotsuite/test_hmm_knn.py
Get-Content -Raw configs/v2_btc_hmm_multi_knn_research.json
rg -n "distance_backend|cupy|CuPy|Lorentzian|knn_settings|dependencies|knn_sweep" docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md tests/tradingbotsuite/test_hmm_knn.py src/tradingbotsuite/research/hmm_knn.py configs/v2_btc_hmm_multi_knn_research.json
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
git diff --check -- src/tradingbotsuite/research/hmm_knn.py tests/tradingbotsuite/test_hmm_knn.py configs/v2_btc_hmm_multi_knn_research.json docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md
git status --short
```

Test result:

```text
35 passed in 15.49s
```

`git diff --check` returned exit code `0` with only LF-to-CRLF warnings.

# Decisions made

- Added `knn.distance_backend` with supported values `cpu`, `auto`, and `cupy`.
- Set the Phase 1 BTC config default to `"cpu"`.
- Kept `lorentzian_distance_matrix()` CPU by default so environments without CuPy, including Python 3.14, continue to work.
- Implemented lazy CuPy loading through `importlib.import_module("cupy")`; CuPy is never imported at module import time and is not a required dependency.
- Implemented `auto` resolution that falls back to CPU when CuPy is not importable or fails a small smoke test.
- Kept explicit `cupy` strict: if requested and unavailable/broken, the research run fails with a clear `RuntimeError`.
- Kept the exact Lorentzian formula and full matrix semantics. No approximate neighbor search was introduced.
- Passed the resolved backend into `_knn_predict()` once per research run so all walk-forward splits use a stable backend.
- Recorded backend choices in artifacts:
  - `knn_settings.distance_backend`
  - `dependencies.knn_distance_backend_requested`
  - `dependencies.knn_distance_backend`
  - `dependencies.cupy_available`
  - `metrics.knn_sweep.distance_backend_requested`
  - `metrics.knn_sweep.distance_backend`
- Added deterministic tests for CPU fallback and fake-CuPy dispatch by monkeypatching the CuPy import path without requiring GPU hardware.

# Assumptions

- Optional CuPy support is a research-speed feature only and does not affect promotion status.
- Explicit `cupy` should fail clearly if unavailable, while `auto` should preserve portability by falling back to CPU.
- Copying the CuPy distance matrix back to NumPy is acceptable for this pass because the existing KNN code still performs exact CPU-side sorting and diagnostics.
- Existing same-regime filtering, K sweep, neighbor diagnostics, and output schemas remain the contract to preserve.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` had no open issues before and after this task. No issue was appended.

# Handoff notes for other agents

- CPU remains the default and the focused suite passes without CuPy.
- `auto` fallback is covered without GPU hardware by monkeypatching the CuPy import path.
- Explicit CuPy selection is available for research environments with the `research-gpu` extra, but it is not evidence of model validity or live readiness.
- Live execution, operator UI, Hyperliquid adapters, sizing, and runtime control files were not touched by this KNN task.
