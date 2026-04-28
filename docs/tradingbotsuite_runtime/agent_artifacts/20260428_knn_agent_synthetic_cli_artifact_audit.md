# Agent name

KNN Agent

# Task received

Independently audit one fresh synthetic `research-hmm-knn` CLI artifact run after the pytest config change. KNN scope: check same-regime diagnostics and K sweep fields. Write a separate work artifact.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_pytest_import_mode_fix.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_distance_pool_sweep_diagnostics_audit.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `tests/tradingbotsuite/test_hmm_knn.py`
- Fresh temp artifact: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_synth_audit_rc52lef9\output\v2-btc-hmm-multi-knn-1\knn_predictions.parquet`
- Fresh temp artifact: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_synth_audit_rc52lef9\output\v2-btc-hmm-multi-knn-1\neighbor_diagnostics.csv`
- Fresh temp artifact: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_synth_audit_rc52lef9\output\v2-btc-hmm-multi-knn-1\walk_forward_metrics.json`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_synthetic_cli_artifact_audit.md`

# Commands/tests run

Shared synthetic CLI run:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main research-hmm-knn --config configs/v2_btc_hmm_multi_knn_research.json --dataset C:\Users\papaa\AppData\Local\Temp\hmm_knn_synth_audit_rc52lef9\synthetic_btcusdt_dataset.parquet --output-dir C:\Users\papaa\AppData\Local\Temp\hmm_knn_synth_audit_rc52lef9\output
```

CLI exit code: `0`.

Inspected `knn_predictions.parquet`, `neighbor_diagnostics.csv`, `walk_forward_metrics.json`, and `artifact_manifest.json` with pandas/json.

# Decisions made

- Confirmed `artifact_manifest.json` records KNN settings from production config: `distance: lorentzian`, `same_regime_only: true`, `allow_cross_regime_fallback: false`, `primary_k: 32`, `primary_weighting: inverse_distance`, `k_values: [16, 24, 32, 48, 64]`, and weightings `inverse_distance` plus `softmax`.
- Confirmed `knn_predictions.parquet` contains the stable prediction fields: `p_up_barrier`, `p_down_barrier`, `expected_net_return_after_costs`, `neighbor_agreement`, `neighbor_distance_quality`, `neighbor_count`, `knn_vote_margin`, `accepted_by_knn`, and `knn_skip_reason`.
- Confirmed `neighbor_diagnostics.csv` contains the required diagnostics fields: `k`, `weighting`, `is_primary`, `same_regime_only`, `fallback_used`, `knn_skip_reason`, `source_row_index`, `query_regime`, `neighbor_rank`, `neighbor_source_index`, `neighbor_distance`, `neighbor_weight`, `neighbor_label_accept`, `neighbor_label_pnl_multiple`, and `neighbor_regime`.
- Confirmed same-regime diagnostics on all populated neighbor rows: every non-null `neighbor_regime` matched `query_regime`.
- Confirmed fallback was not used in this default-config run: diagnostic `fallback_used` values were only `false`.
- Confirmed K sweep coverage in diagnostics and metrics: diagnostics included K values `16`, `24`, `32`, `48`, and `64`, and both weighting modes.
- Confirmed `walk_forward_metrics.json` had 10 K sweep results: all five K values crossed with `inverse_distance` and `softmax`; only `(32, inverse_distance)` was marked primary.
- Observed diagnostic skip reasons: `160` `insufficient_neighbors` rows and `1600` successful neighbor rows marked as `none`.

# Assumptions

- A diagnostic row with null neighbor fields and `knn_skip_reason = insufficient_neighbors` is expected for combinations that cannot meet minimum neighbor count in a small synthetic run.
- Because `allow_cross_regime_fallback` is false in production config, fallback absence is the expected result.
- The temp synthetic run is sufficient for artifact-shape and policy validation; it is not intended to prove strategy performance.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues before this audit.

# Handoff notes for other agents

- Fresh synthetic CLI KNN artifact audit passed.
- Generated `knn_predictions.parquet` had 32 rows and `neighbor_diagnostics.csv` had 1760 rows.
- K sweep behavior is visible in both diagnostics and metrics.
- Same-regime enforcement held for all populated diagnostic neighbors, and cross-regime fallback stayed disabled.
- No code, config, live execution, sizing, gates, or operator controls were changed.
