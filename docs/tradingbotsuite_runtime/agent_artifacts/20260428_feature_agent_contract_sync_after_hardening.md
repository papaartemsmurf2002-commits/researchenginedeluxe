# Feature Agent Contract Sync After Hardening

## Agent

Feature Agent

## Task Received

Sync public contracts for any new hardening fields after Regime, KNN, Meta, Data, and Labeling updates. Update Markdown only if public artifact fields were added or clarified. Keep the docs aligned with BTC Phase 1 and the research-only boundary.

## Commands Run

```powershell
rg -n "feature_columns|label_outcome_fields|neighbor_diagnostics|regime_posteriors|meta_backend|missing_feature_rates" docs/tradingbotsuite_runtime src tests
```

Additional scoped checks:

```powershell
rg -n "LABEL_OUTCOME_COLUMNS|WT3D_FEATURE_COLUMNS|KNN_OUTPUT_COLUMNS|manifest =|dependencies|missing_feature_rates|neighbor_distance_quality|neighbor_diagnostics|regime_posteriors|meta_backend" src\tradingbotsuite\research\hmm_knn.py src\tradingbotsuite\research\dataset.py
rg -n "test_public_feature_columns|label_outcome_fields|missing_feature_rates|meta_backend|neighbor_distance_quality|regime_posteriors|neighbor_diagnostics" tests\tradingbotsuite\test_hmm_knn.py tests\tradingbotsuite\test_research.py tests\test_research.py
rg -n "dataset_manifest|missing_feature_rates|meta_backend|neighbor_distance_quality|regime_model_backend|source_row_index|top_regime_label|label_outcome_fields" docs\tradingbotsuite_runtime
```

## Files Read

- `src/tradingbotsuite/research/dataset.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `tests/tradingbotsuite/test_research.py`
- `tests/test_research.py`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- Related prior agent artifacts surfaced by the contract search.

## Files Changed

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_feature_agent_contract_sync_after_hardening.md`

## Contract Sync Decisions

- Documented the BTC Phase 1 `dataset_manifest.json` public Data/Labeling contract in the model spec, including `label_outcome_fields`, `missing_feature_rates`, `raw_context_available_counts`, `exchange_context_summary`, and `planned_split_summary`.
- Clarified the `regime_posteriors.parquet` public Regime contract with `regime_model_backend`, `walk_forward_split`, and `source_row_index` in addition to posterior, confidence, flip, no-trade, and train-fit marker fields.
- Kept the KNN public contract aligned with the hardened diagnostics: `neighbor_distance_quality` is public in both KNN predictions and neighbor diagnostics.
- Clarified the Meta public contract: `meta_predictions.parquet` emits `meta_model_backend`, while `artifact_manifest.json` exposes `dependencies.meta_backend` and `dependencies.xgboost_available`.
- Repeated the research-only boundary where these fields are documented: hardening fields are diagnostics and audit inputs only, not live gates, sizing, Hyperliquid execution, safety behavior, or operator live controls.

## Validation Notes

- No Python or tests were changed.
- No tests were run because the requested work was Markdown-only.
- The source/test search confirmed the public field contracts are already asserted in code or tests for `label_outcome_fields`, `missing_feature_rates`, `neighbor_distance_quality`, `regime_posteriors`, and `meta_backend`.

## Open Issues

- None for this Markdown-only contract sync.

## Handoff Notes

- Future Regime/KNN/Meta/Data/Labeling hardening should update `HMM_MULTI_KNN_MODEL_SPEC.md` first, then mirror agent-specific public contract expectations into `HMM_MULTI_KNN_AGENT_PROMPTS.md`.
- Fresh BTC Phase 1 research artifacts should be preferred when auditing these contracts because older generated manifests may predate `missing_feature_rates`, `raw_context_available_counts`, `exchange_context_summary`, or `dependencies.meta_backend`.
