# Feature Agent Public Contract Freeze

## Agent

Feature Agent

## Task Received

Prepare final public contract freeze notes after the hardening pass. Review public artifact fields, update Markdown only if stale, and list schema/version fields that should not change casually.

## Command Run

```powershell
rg -n "feature_version|feature_columns|label_outcome_fields|regime_posteriors|neighbor_diagnostics|meta_predictions|monitoring_report" docs/tradingbotsuite_runtime src tests configs
```

Additional scoped checks:

```powershell
rg -n "HMM_KNN_FEATURE_VERSION|HMM_KNN_ARTIFACT_MANIFEST_VERSION|HMM_KNN_MONITORING_REPORT_VERSION|monitoring_report_version|research_only|observe_only|promotion_ready" src\tradingbotsuite\research\hmm_knn.py src\tradingbotsuite\research\hmm_knn_monitoring.py tests\tradingbotsuite\test_hmm_knn.py docs\tradingbotsuite_runtime\HMM_MULTI_KNN_MODEL_SPEC.md
rg -n "RESEARCH_FEATURE_VERSION|DATASET_MANIFEST_VERSION|LABEL_VERSION" src\tradingbotsuite\core\features.py src\tradingbotsuite\research\dataset.py tests\test_research.py tests\tradingbotsuite\test_research.py
rg -n "metrics_version|HMM_KNN_METRICS_VERSION|walk_forward_metrics_version|v2-hmm-knn-walk-forward-metrics" src\tradingbotsuite\research\hmm_knn.py tests\tradingbotsuite\test_hmm_knn.py docs\tradingbotsuite_runtime\HMM_MULTI_KNN_MODEL_SPEC.md
```

## Files Read

- `configs/v2_btc_hmm_multi_knn_research.json`
- `src/tradingbotsuite/core/features.py`
- `src/tradingbotsuite/research/dataset.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `src/tradingbotsuite/research/hmm_knn_monitoring.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `tests/tradingbotsuite/test_research.py`
- `tests/test_research.py`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_RUNBOOK.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_SOURCE_LOG.md`

## Files Changed

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_feature_agent_public_contract_freeze.md`

## Public Contract Freeze

The following schema and version fields are public research contracts. Do not rename, remove, reinterpret, or bump them casually. Any change should include coordinated updates to docs, tests, fixture expectations, replay behavior, monitoring behavior, and downstream artifact readers.

### Version Fields

- Dataset manifest: `dataset_manifest_version = v2-dataset-manifest-1`
- Dataset feature snapshots: `feature_version = v2-btc-acceptance-2`
- HMM/KNN artifact manifest: `artifact_manifest_version = v2-hmm-knn-artifact-manifest-1`
- HMM/KNN feature contract: `feature_version = v2-btc-hmm-knn-features-1`
- HMM/KNN meta rows: `hmm_knn_feature_version = v2-btc-hmm-knn-features-1`
- Walk-forward metrics: `metrics_version = v2-hmm-knn-walk-forward-metrics-1`
- Monitoring report: `monitoring_report_version = v2-hmm-knn-monitoring-report-1`
- Label contract: `label_version = triple_barrier_live_parity_v1`

### Dataset Manifest Fields

- `research_only`
- `symbol`
- `asset_scope`
- `feature_version`
- `label_version`
- `label_outcome_fields`
- `missing_feature_rates`
- `raw_context_available_counts`
- `exchange_context_summary`
- `planned_split_summary`
- `dataset_path`
- `dataset_sha256`
- `row_count`

### HMM/KNN Artifact Manifest Fields

- `artifact_manifest_version`
- `plan_version`
- `plan_sha256`
- `research_only`
- `symbol`
- `asset_scope`
- `config_path`
- `dataset_path`
- `row_count`
- `feature_version`
- `feature_columns`
- `wt3d_feature_columns`
- `label_version`
- `label_horizons`
- `primary_label_horizon`
- `label_outcome_fields`
- `knn_settings`
- `regime_posteriors_path`
- `knn_predictions_path`
- `meta_predictions_path`
- `neighbor_diagnostics_path`
- `metrics_path`
- `dependencies.hmm_backend`
- `dependencies.meta_backend`
- `dependencies.hmmlearn_available`
- `dependencies.xgboost_available`
- `meta_validation`
- `outputs`

### Public Artifact Files And Fields

- `regime_posteriors.parquet`: posterior columns `regime_p_0...`, `top_regime`, `top_regime_label`, `max_regime_probability`, `posterior_entropy`, `recent_regime_flip`, `regime_no_trade`, `regime_model_backend`, `walk_forward_split`, `source_row_index`, and `hmm_fit_end_row`.
- `knn_predictions.parquet`: `p_up_barrier`, `p_down_barrier`, `expected_net_return_after_costs`, `neighbor_agreement`, `neighbor_distance_quality`, `neighbor_count`, `neighbor_min_source_index`, `neighbor_max_source_index`, `knn_vote_margin`, `accepted_by_knn`, and `knn_skip_reason`.
- `meta_predictions.parquet`: `hmm_knn_feature_version`, regime outputs, KNN outputs, WT3D feature columns, configured public KNN feature columns, `meta_probability`, `meta_model_backend`, `accepted_by_meta`, and all current `label_outcome_fields`.
- `neighbor_diagnostics.csv`: `k`, `weighting`, `is_primary`, `same_regime_only`, `fallback_used`, `knn_skip_reason`, `source_row_index`, `query_regime`, `neighbor_rank`, `neighbor_source_index`, `neighbor_distance`, `neighbor_distance_quality`, `neighbor_weight`, `neighbor_label_accept`, `neighbor_label_pnl_multiple`, and `neighbor_regime`.
- `walk_forward_metrics.json`: `metrics_version`, `research_only`, `promotion_ready`, `promotion_failures`, `knn_sweep`, `meta_validation`, `evaluation_basis`, and `comparison`.
- `monitoring_report.json`: `monitoring_report_version`, `research_only`, `observe_only`, `promotion_ready`, `artifact_identity`, `artifact_files`, `source_metrics`, `feature_outages`, `entropy_no_trade`, `regime_distribution_drift`, `neighbor_quality`, `funding_costs`, `calibration_decay`, `live_vs_replay_mismatch`, and `alerts`.

## Research Boundary

All contracts above remain BTC Phase 1 and research-only. They are audit, replay, monitoring, and documentation contracts. They must not be treated as live execution signals, live gates, live sizing inputs, Hyperliquid execution changes, safety behavior changes, or operator live-control permissions without a separate explicit approval pass.

## Validation Notes

- No Python or test files were changed.
- No tests were run because this task was Markdown-only.
- The model spec was updated because `monitoring_report.json` had only been referenced in validation notes, not listed as a public artifact contract.

## Open Issues

- None for this Markdown-only freeze pass.
