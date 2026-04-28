# Agent name

Regime Agent

# Task received

Independently audit one fresh synthetic `research-hmm-knn` CLI artifact run after the pytest config change. Regime scope: check posterior, no-trade, and entropy fields. Write a separate work artifact.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_pytest_import_mode_fix.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_regime_agent_hmm_regime_audit.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_distance_pool_sweep_diagnostics_audit.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_meta_model_agent_audit.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `tests/tradingbotsuite/test_hmm_knn.py`
- Fresh temp artifact: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_synth_audit_rc52lef9\output\v2-btc-hmm-multi-knn-1\regime_posteriors.parquet`
- Fresh temp artifact: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_synth_audit_rc52lef9\output\v2-btc-hmm-multi-knn-1\artifact_manifest.json`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_regime_agent_synthetic_cli_artifact_audit.md`

# Commands/tests run

Created the synthetic fixture dataset from the existing test helper:

```powershell
$env:PYTHONPATH='src;.'; @'
from tests.tradingbotsuite.test_hmm_knn import _synthetic_dataset
# wrote 120-row synthetic_btcusdt_dataset.parquet under a temp directory
'@ | python -
```

Ran the real CLI with production config:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main research-hmm-knn --config configs/v2_btc_hmm_multi_knn_research.json --dataset C:\Users\papaa\AppData\Local\Temp\hmm_knn_synth_audit_rc52lef9\synthetic_btcusdt_dataset.parquet --output-dir C:\Users\papaa\AppData\Local\Temp\hmm_knn_synth_audit_rc52lef9\output
```

CLI exit code: `0`.

Inspected `regime_posteriors.parquet`, `artifact_manifest.json`, and `walk_forward_metrics.json` with pandas/json.

# Decisions made

- Treated the temp run as an independent artifact audit, separate from pytest-only validation.
- Confirmed the artifact is BTC-only and research-only: manifest `symbol` is `BTCUSDT`, `asset_scope` is `["BTCUSDT"]`, and `research_only` is `true`.
- Confirmed `regime_posteriors.parquet` contains the required regime fields: `regime_p_0`, `regime_p_1`, `regime_p_2`, `regime_p_3`, `top_regime`, `top_regime_label`, `max_regime_probability`, `posterior_entropy`, `recent_regime_flip`, `regime_no_trade`, `hmm_fit_end_row`.
- Confirmed posterior probabilities are normalized in the generated artifact: row posterior sums min `1.0`, max `1.0`.
- Confirmed the synthetic run used the deterministic fallback backend in this environment: `gaussian_mixture_fallback`; manifest reports `hmmlearn_available: false`.
- Confirmed train/test ordering guard in the artifact: `hmm_fit_end_row < source_row_index` for all 32 regime rows.
- Confirmed entropy and no-trade fields are populated: entropy min and max were both `5.979470570797252e-11`; `regime_no_trade` rate was `0.0` for this synthetic run.

# Assumptions

- The synthetic dataset helper in `tests/tradingbotsuite/test_hmm_knn.py` is the intended fallback fixture when no small checked-in HMM/KNN dataset exists.
- The run being after the pytest config change is established by prior artifact `20260428_backtest_agent_pytest_import_mode_fix.md`, which records `addopts = "--import-mode=importlib"` and a green full suite.
- The low entropy and zero no-trade rate are properties of this clean synthetic dataset, not a general production expectation.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues before this audit.

# Handoff notes for other agents

- Fresh synthetic CLI regime artifact audit passed.
- Output directory audited: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_synth_audit_rc52lef9\output\v2-btc-hmm-multi-knn-1`.
- Regime output had 32 rows across two evaluated walk-forward splits: split `0` had 16 rows and split `1` had 16 rows.
- No code, config, live execution, sizing, gates, or operator controls were changed.
