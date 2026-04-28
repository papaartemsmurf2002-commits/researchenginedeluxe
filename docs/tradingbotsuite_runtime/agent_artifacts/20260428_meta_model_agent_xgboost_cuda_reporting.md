# Agent name

Meta-Model Agent

# Task received

Add optional XGBoost CUDA backend detection/reporting.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `src/tradingbotsuite/research/hmm_knn.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- Relevant prior Meta/Backtest artifacts surfaced by `rg` for XGBoost metadata and experiment planning.

# Files changed

- `src/tradingbotsuite/research/hmm_knn.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_meta_model_agent_xgboost_cuda_reporting.md`
- `pyproject.toml`
- `configs/v2_btc_hmm_multi_knn_research.json`

# Commands/tests run

```powershell
rg -n "XGBClassifier|xgboost_available|meta_backend|dependencies|artifact_manifest|MetaModelSettings|_fit_meta_model" src\tradingbotsuite\research\hmm_knn.py tests\tradingbotsuite\test_hmm_knn.py docs\tradingbotsuite_runtime configs\v2_btc_hmm_multi_knn_research.json
```

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
```

Result:

```text
27 passed in 13.10s
```

```powershell
rg -n "xgboost_cuda|_xgboost_cuda_dependency_report|XGBClassifier|xgboost_available|meta_backend" src\tradingbotsuite\research\hmm_knn.py tests\tradingbotsuite\test_hmm_knn.py docs\tradingbotsuite_runtime\HMM_MULTI_KNN_MODEL_SPEC.md docs\tradingbotsuite_runtime\agent_artifacts
```

```powershell
$env:PYTHONPATH='src'; python <temporary manifest smoke script>
```

Result in the current default environment:

```json
{"xgboost_available": false, "xgboost_cuda_available": false, "xgboost_cuda_detection": "xgboost_unavailable"}
```

# Decisions made

- Added optional XGBoost CUDA reporting to `artifact_manifest.json` under the existing `dependencies` block.
- Kept detection separate from training. The research job does not try to force GPU execution or probe hardware; it only reads XGBoost build metadata when XGBoost is importable.
- Added the following manifest dependency fields:
  - `dependencies.xgboost_cuda_available`
  - `dependencies.xgboost_cuda_detection`
  - optional `dependencies.xgboost_cuda_build_info`
  - optional `dependencies.xgboost_cuda_error` if build-info detection raises
- Detection values:
  - `xgboost_unavailable` when XGBoost is not importable
  - `build_info_unavailable` when XGBoost lacks a callable `build_info`
  - `build_info_error` when build-info probing fails
  - `build_info` when build metadata was read
- Added test coverage for:
  - unavailable XGBoost/fallback manifest reporting, including CUDA unavailable metadata
  - CUDA-enabled fake XGBoost build-info metadata
  - non-CUDA fake XGBoost build-info metadata where string values such as `"OFF"` are treated as false
- Updated the public model spec so the new dependency metadata is documented as a research artifact contract field.
- Orchestrator follow-up made GPU acceleration executable but still optional:
  - added `research-gpu` optional dependencies in `pyproject.toml`
  - added `meta_model.device: "auto"` and `meta_model.tree_method: "hist"` to the Phase 1 config
  - added XGBoost device resolution so `auto` uses `cuda` only when XGBoost build metadata reports CUDA support
  - records actual meta backend as `xgboost_cuda` when the CUDA device is selected
  - added focused test coverage for the fake CUDA build selecting `device="cuda"` and `tree_method="hist"`

# Assumptions

- "CUDA backend detection/reporting" remains research-only. The orchestrator follow-up permits XGBoost training to select CUDA inside research runs when `meta_model.device` is `auto` or `cuda`, but this does not create a live runtime execution path.
- XGBoost build metadata is the least invasive reliable signal for this task. Hardware-level CUDA availability should be a separate environment/preflight concern if needed.
- The fields are diagnostic metadata only and remain BTC Phase 1 research-only.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` had no open issues before implementation. No new issue was appended.

# Handoff notes for other agents

- Future XGBoost research-extra runs should check both `dependencies.xgboost_available` and `dependencies.xgboost_cuda_available` before interpreting backend performance.
- A CUDA-capable build plus `meta_model.device: auto` means the research meta-model should request XGBoost `device="cuda"` and report `meta_model_backend: xgboost_cuda`. This is an acceleration detail, not promotion evidence.
- This change does not alter live gates, sizing, Hyperliquid execution, operator controls, or promotion readiness.
