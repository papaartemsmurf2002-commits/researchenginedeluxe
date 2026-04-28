# Agent name

KNN Agent

# Task received

Independently audit one synthetic `research-hmm-knn` artifact run after the pytest config change. Use a temp output directory and verify KNN same-regime diagnostics and K sweep fields.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_distance_pool_sweep_diagnostics_audit.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_pytest_import_mode_fix.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `tests/tradingbotsuite/test_hmm_knn.py`
- Generated artifact: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1\knn_predictions.parquet`
- Generated artifact: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1\neighbor_diagnostics.csv`
- Generated artifact: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1\walk_forward_metrics.json`
- Generated artifact: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1\artifact_manifest.json`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_synthetic_artifact_run_audit.md`

# Commands/tests run

```powershell
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_PROMPTS.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_ISSUES.md
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_knn_agent_distance_pool_sweep_diagnostics_audit.md
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_backtest_agent_pytest_import_mode_fix.md
$env:PYTHONPATH='src'; python -m tradingbotsuite.main research-hmm-knn --config configs/v2_btc_hmm_multi_knn_research.json --dataset "C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\synthetic_btcusdt_hmm_knn.parquet" --output-dir "C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output"
```

Artifact inspection was performed with a Python script reading `knn_predictions.parquet`, `neighbor_diagnostics.csv`, `walk_forward_metrics.json`, and `artifact_manifest.json`.

# Decisions made

- Used the same real CLI artifact run as the Regime and Meta audits so all three artifacts refer to one consistent synthetic output set.
- Confirmed the generated `knn_predictions.parquet` has 48 rows and 16 columns.
- Confirmed primary KNN prediction fields are present: `p_up_barrier`, `p_down_barrier`, `expected_net_return_after_costs`, `neighbor_agreement`, `neighbor_distance_quality`, `neighbor_count`, `neighbor_min_source_index`, `neighbor_max_source_index`, `knn_vote_margin`, `accepted_by_knn`, `knn_skip_reason`, and `walk_forward_split`.
- Observed `accepted_by_knn` count `0` on this synthetic run. This is acceptable for an artifact schema/diagnostics audit because promotion or profitability was not expected from the synthetic fixture.
- Confirmed primary rows had no KNN skip reason: `knn_skip_reason` count was `None: 48`.
- Confirmed neighbor counts ranged from `18` to `32`, satisfying the production config minimum neighbor count of `8`.
- Confirmed `neighbor_diagnostics.csv` has 4,800 rows and 20 columns.
- Confirmed diagnostics include `k`, `weighting`, `is_primary`, `same_regime_only`, `fallback_used`, `knn_skip_reason`, `source_row_index`, `query_regime`, `neighbor_rank`, `neighbor_source_index`, `neighbor_distance`, `neighbor_weight`, `neighbor_label_accept`, `neighbor_label_pnl_multiple`, and `neighbor_regime`.
- Confirmed configured K sweep values are present in diagnostics: `16`, `24`, `32`, `48`, and `64`.
- Confirmed configured weighting modes are present in diagnostics: `inverse_distance` and `softmax`.
- Confirmed same-regime behavior: `same_regime_only` is always `true`, `fallback_used_count` is `0`, and cross-regime neighbor rows count is `0`.
- Confirmed manifest `knn_settings` records `distance: lorentzian`, `same_regime_only: true`, `allow_cross_regime_fallback: false`, `primary_k: 32`, `primary_weighting: inverse_distance`, configured K values, and configured weighting modes.
- Confirmed `walk_forward_metrics.json` includes a `knn_sweep` section with configured K values, configured weighting, primary K, primary weighting, same-regime flag, fallback flag, and result entries for the K/weighting combinations.

# Assumptions

- Same-regime diagnostics can be audited by comparing diagnostic `query_regime` and `neighbor_regime` fields when `neighbor_regime` is present.
- K sweep verification is satisfied by the diagnostics and metrics output containing all configured K values and weighting modes.
- Zero accepted synthetic KNN rows is not an error because the fixture is not intended to prove trading edge.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues before this run.

# Handoff notes for other agents

- The CLI-generated diagnostics enforce same-regime neighbor selection for this synthetic run.
- The K sweep path is observable in both `neighbor_diagnostics.csv` and `walk_forward_metrics.json`.
- No cross-regime fallback occurred, matching the production config.
- The artifact output directory is `C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1`.
