# Agent name

Data Agent

# Task received

Objective: make fixture data assumptions explicit and auditable.

Commands requested:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py -q
rg -n "fixture|btc_15m_fixture|asset_scope|BTCUSDT|missing_feature_rates|exchange_context_summary|raw_context_available_counts" tests src docs/tradingbotsuite_runtime configs
```

Tasks:

- Verify the fixture dataset used by CLI/E2E tests represents BTC Phase 1 and has enough columns for HMM/KNN artifact generation.
- If missingness assumptions are implicit, add docs or tests that make them explicit.
- Ensure no fixture path relies on live Binance calls.
- Write this artifact.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_cli_e2e_fixture_validation.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_regime_agent_synthetic_cli_artifact_audit.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_meta_model_agent_backend_regression_hardening.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_missing_context_manifest_hardening.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `tests/tradingbotsuite/test_research.py`

# Files changed

- `tests/tradingbotsuite/test_hmm_knn.py`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_fixture_dataset_readiness.md`

# Commands/tests run

```powershell
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_PROMPTS.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_ISSUES.md
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py -q
rg -n "fixture|btc_15m_fixture|asset_scope|BTCUSDT|missing_feature_rates|exchange_context_summary|raw_context_available_counts" tests src docs/tradingbotsuite_runtime configs
rg -n "_synthetic_dataset|research-hmm-knn|monitor-hmm-knn|CliRunner|subprocess|fixture dataset|fixture_dataset|BTCUSDT|asset_scope|missing_feature_rates|exchange_context_summary|raw_context_available_counts" tests\tradingbotsuite\test_hmm_knn.py tests\tradingbotsuite tests docs\tradingbotsuite_runtime\agent_artifacts
rg -n -C 30 "def _cmd_research_hmm_knn|research-hmm-knn|run_hmm_knn_research|Binance|Candle|dataset" src\tradingbotsuite\main.py src\tradingbotsuite\research\hmm_knn.py
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
rg -n "fixture|btc_15m_fixture|asset_scope|BTCUSDT|missing_feature_rates|exchange_context_summary|raw_context_available_counts" tests src docs/tradingbotsuite_runtime configs
```

Validation results:

```text
tests/tradingbotsuite/test_research.py: 13 passed in 3.43s
tests/tradingbotsuite/test_hmm_knn.py: 23 passed in 11.63s
```

# Decisions made

- Added `test_hmm_knn_synthetic_fixture_contract_is_btc_phase_1_and_offline` to `tests/tradingbotsuite/test_hmm_knn.py`.
- The new test makes the HMM/KNN synthetic fixture contract executable:
  - fixture rows are BTC Phase 1 only: `symbol == BTCUSDT`;
  - config `asset_scope` is `["BTCUSDT"]`;
  - rows are 15-minute spaced by `tv_bar_time_ms`;
  - labels contain both classes;
  - all static HMM/KNN required input columns are present before artifact generation;
  - `_prepare_dataset()` expands the fixture into all configured KNN features, HMM emission features, WT3D features, and public label outcome fields.
- Made missingness assumptions explicit for the HMM/KNN synthetic fixture:
  - the fixture intentionally does not model dataset-builder raw exchange context;
  - no `raw_*`, `missing_*`, or `*_context_json` columns are present in the synthetic fixture input;
  - the fixture does carry normalized perp context columns such as `funding_rate`, `funding_rate_change`, `open_interest_change_pct`, and `premium_basis_rate`;
  - dataset-builder raw-null plus `missing_*` behavior remains covered in `tests/tradingbotsuite/test_research.py`.
- Tightened `test_hmm_knn_cli_research_then_monitor_writes_expected_temp_artifacts` so the generated artifact manifest must report:
  - `symbol: BTCUSDT`;
  - `asset_scope: ["BTCUSDT"]`;
  - `dataset_path` equal to the explicit pytest `tmp_path` fixture parquet;
  - `feature_columns` equal to the config KNN feature columns.
- Verified the CLI/E2E path passes `--dataset <tmp parquet>` and `--output-dir <tmp dir>` to `research-hmm-knn`, then passes only the generated manifest to `monitor-hmm-knn`. This path calls `run_hmm_knn_research()` on a local parquet and does not invoke `build-dataset`, `AppConfig.from_env()`, `BinanceCandleClient`, or live Binance fetch/bootstrap paths.

# Assumptions

- "Fixture dataset used by CLI/E2E tests" refers to `_synthetic_dataset()` in `tests/tradingbotsuite/test_hmm_knn.py`, which is written to a pytest temp Parquet and passed to the CLI by `test_hmm_knn_cli_research_then_monitor_writes_expected_temp_artifacts`.
- The HMM/KNN synthetic fixture is an artifact-generation fixture, not a full Data Agent raw-context dataset fixture. Raw context and missingness manifest behavior belongs to the generated dataset builder tests in `tests/tradingbotsuite/test_research.py`.
- Existing dirty or untracked files outside this task belong to the active multi-agent workstream and were not reverted.
- Phase 1 remains BTC-only and research-only; no live execution, gate, sizing, Hyperliquid, safety, or operator live-control behavior was touched.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues before this task. No new issue was appended.

# Handoff notes for other agents

- The HMM/KNN CLI/E2E fixture is now explicitly audited as BTC-only, local-temp, and sufficient for artifact generation.
- Do not use the HMM/KNN synthetic fixture as evidence that raw exchange context was observed; it intentionally uses normalized synthetic context only.
- Use the Data Agent builder tests for raw exchange context and missingness manifest guarantees, and use the HMM/KNN fixture tests for downstream artifact-generation readiness.
- Future fixture expansions that add raw context columns should also add matching `missing_*` and manifest checks, or keep those concerns in the dataset-builder fixture path.
