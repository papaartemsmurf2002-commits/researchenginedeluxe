# Agent name

Regime Agent

# Task received

Audit HMM train-only fitting, forward-only posterior output, entropy/no-trade behavior, and optional `hmmlearn` fallback behavior. The user explicitly requested looking up `HMM_MULTI_KNN_AGENT_PROMPTS.md` before action and writing a work artifact.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_INPUT_LOOKUP.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_RUNBOOK.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_SOURCE_LOG.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_first_hmm_knn_sweep_validation.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_runtime_adjacent_review.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_feature_agent_lookup_protocol_feature_contract.md`
- `src/tradingbotsuite/research/hmm_knn.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `tests/tradingbotsuite/test_research.py`
- `pyproject.toml`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_regime_agent_hmm_regime_audit.md`

# Commands/tests run

```powershell
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_PROMPTS.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_ISSUES.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_MODEL_SPEC.md
Get-ChildItem -Force docs\tradingbotsuite_runtime\agent_artifacts
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_INPUT_LOOKUP.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_REALIZATION_PLAN.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_RUNBOOK.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_SOURCE_LOG.md
Get-Content configs\v2_btc_hmm_multi_knn_research.json
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_backtest_agent_first_hmm_knn_sweep_validation.md
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_execution_risk_runtime_adjacent_review.md
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_feature_agent_lookup_protocol_feature_contract.md
rg -n "GaussianHMM|RegimeModel|_normalize_posterior|_fit_regime_model|_label_states|_posterior_frame|robust_scaler_fit\(train_frame|regime_model.posterior|regime_no_trade|hmm_fit_end_row" src\tradingbotsuite\research\hmm_knn.py
rg -n "train_only|forward_only|future|uncertain|hmmlearn|fallback|regime_fit|posterior|regime_no_trade|model_spec" tests\tradingbotsuite\test_hmm_knn.py
rg -n "research|hmmlearn|xgboost|optional-dependencies" pyproject.toml
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_hmm_knn.py -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_research.py -q
```

Exact test results:

```text
tests\tradingbotsuite\test_hmm_knn.py: 18 passed in 5.05s
tests\tradingbotsuite\test_research.py: 11 passed in 3.49s
```

# Decisions made

- Treated this task as an audit and handoff task. No runtime, live execution, live gates, sizing, Hyperliquid behavior, safety behavior, or operator live controls were changed.
- Confirmed `HMM_MULTI_KNN_AGENT_ISSUES.md` has no open issues, so no stop condition was triggered.
- Confirmed the HMM regime model is fit only from walk-forward `train_frame` data. In `run_hmm_knn_research`, the HMM scaler is fit with `robust_scaler_fit(train_frame, plan.hmm.emission_features)`, the model receives `hmm_scaler.transform(train_frame)`, and the test posterior receives only transformed `test_frame` after fitting.
- Confirmed HMM output includes the required regime artifact fields: posterior probability columns, `top_regime`, `top_regime_label`, `max_regime_probability`, `posterior_entropy`, `recent_regime_flip`, `regime_no_trade`, `regime_model_backend`, `walk_forward_split`, `source_row_index`, and `hmm_fit_end_row`.
- Confirmed `hmmlearn` live-style posterior output does not use future-smoothed Viterbi states. The `RegimeModel` path uses `_hmm_online_posterior`, which applies a forward alpha update over emissions and transition probabilities, then records the row posterior before advancing to the next row.
- Confirmed fallback output is deterministic in default environments without the optional research dependency. When `plan.hmm.backend` is `auto` or `hmmlearn`, `GaussianHMM` is used only if import succeeds and there are at least `n_states * 3` train rows. Otherwise the code uses `GaussianMixture(..., covariance_type="diag", random_state=plan.hmm.random_state, max_iter=plan.hmm.max_iter)`.
- Confirmed posterior values are defensively normalized through `_normalize_posterior`, including padding/truncating state columns to the configured state count, replacing non-finite values with zero, and assigning uniform uncertainty to rows with non-positive posterior mass.
- Confirmed state labels are assigned from observed train statistics (`directional_slope_atr`, `realized_volatility`, and `choppiness`) rather than stable component IDs. The current four-state mapping labels shock, bull, bear, and range/chop from train-row summary statistics and uses deterministic tie-breakers.
- Confirmed no-trade behavior follows the prompt and config. A row is blocked when top posterior probability is below `plan.hmm.posterior_threshold`, normalized entropy exceeds `plan.hmm.entropy_threshold`, or the top state flipped within `plan.hmm.flip_cooldown_bars`.

# Assumptions

- The audit scope is limited to BTC Phase 1 research HMM regime routing and its tests.
- Resetting the online HMM filter at the start of each scoring matrix is acceptable for the current walk-forward artifact; it avoids future smoothing and does not leak validation/test rows into fitting.
- The Gaussian mixture fallback is an acceptable deterministic non-HMM fallback because the prompt requires default environments without optional research packages to remain runnable.
- Prior artifacts from the Backtest, Feature, and Execution/Risk agents are part of the active workstream and influenced this audit.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues before this audit, and this audit did not uncover a blocker requiring a new issue.

# Handoff notes for other agents

- Regime routing is currently research-only and BTC-only.
- HMM train-only fitting and forward-only posterior behavior are covered by tests in `tests/tradingbotsuite/test_hmm_knn.py`, including:
  - `test_hmm_online_posterior_is_forward_only_for_prefix_rows`
  - `test_uncertain_regime_posterior_sets_no_trade_flag`
  - `test_regime_fit_ignores_rows_after_current_test_split`
- Optional dependency behavior is documented in `HMM_MULTI_KNN_SOURCE_LOG.md` and encoded in `pyproject.toml` under the `research` extra with `hmmlearn==0.3.3`.
- If later agents change the regime model to carry alpha state across train/test boundaries, they must add a specific no-leakage test for that handoff state.
- If later agents change `hmm.backend` semantics, keep the manifest backend reporting and default deterministic fallback intact.
