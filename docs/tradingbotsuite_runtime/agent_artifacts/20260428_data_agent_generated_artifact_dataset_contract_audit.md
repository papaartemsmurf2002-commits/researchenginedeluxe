# Agent name

Data Agent

# Task received

Audit the same generated/reused artifact manifest and parquet/csv outputs for dataset contract consistency. Data checks: BTC-only scope, missingness fields, raw context summaries, and no fabricated exchange context. Write a separate artifact.

# Reused artifact set

- Artifact manifest: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1\artifact_manifest.json`
- Referenced dataset parquet: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\synthetic_btcusdt_hmm_knn.parquet`
- HMM/KNN outputs:
  - `regime_posteriors.parquet`
  - `knn_predictions.parquet`
  - `meta_predictions.parquet`
  - `neighbor_diagnostics.csv`
  - `walk_forward_metrics.json`

# Files read

- `artifact_manifest.json` from the reused artifact set above
- Referenced synthetic dataset parquet
- `regime_posteriors.parquet`
- `knn_predictions.parquet`
- `meta_predictions.parquet`
- `neighbor_diagnostics.csv`
- `walk_forward_metrics.json`
- `data/research/v2-btc-research-1/dataset_manifest.json`
- Prior agent artifacts under `docs/tradingbotsuite_runtime/agent_artifacts/`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_generated_artifact_dataset_contract_audit.md`

# Commands/tests run

```powershell
Get-ChildItem -Recurse -Force -File data\research -Include artifact_manifest.json,dataset_manifest.json,*.parquet,*.csv
Test-Path C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1\artifact_manifest.json
Get-Content C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1\artifact_manifest.json
$env:PYTHONPATH='src'; python <artifact inspection script>
```

The inspection script loaded the artifact manifest, referenced dataset parquet, all HMM/KNN parquet/csv outputs, and metrics JSON with pandas/json.

# Audit results

## BTC-only scope

Pass for the reused artifact set.

- Manifest `symbol`: `BTCUSDT`
- Manifest `asset_scope`: `["BTCUSDT"]`
- Dataset parquet symbols: `["BTCUSDT"]`
- `regime_posteriors.parquet` symbols: `["BTCUSDT"]`
- `knn_predictions.parquet` symbols: `["BTCUSDT"]`
- `meta_predictions.parquet` symbols: `["BTCUSDT"]`
- `neighbor_diagnostics.csv` symbols: `["BTCUSDT"]`

The reused artifact set is BTC-only and matches Phase 1 scope.

## Dataset shape and source

The referenced dataset parquet is synthetic/minimal:

- Shape: `180 rows x 28 columns`
- Source counts: `{"tradingview": 180}`
- Columns present include signal identity, symbol, direction, entry price, primary labels, and selected model feature columns.

This is not a full `ResearchDatasetBuilder` output and does not include a paired `dataset_manifest.json`.

## Missingness fields

Contract gap for the reused artifact set.

- Dataset `missing_*` column count: `0`
- Meta predictions `missing_*` column count: `0`
- Manifest does not contain `missing_feature_rates`.

The synthetic artifact is valid for HMM/KNN model-shape testing, but it does not satisfy the full dataset-builder missingness contract required for production-style research data.

## Raw context summaries

Contract gap for the reused artifact set.

Absent from the artifact manifest:

- `raw_context_available_counts`
- `exchange_context_summary`

Absent from the referenced dataset parquet:

- `raw_*` audit columns
- `funding_context_json`
- `open_interest_context_json`
- `premium_context_json`
- `microstructure_context_json`
- `basis_context_json`

The real repo dataset manifest at `data/research/v2-btc-research-1/dataset_manifest.json` also predates the newest manifest fields and does not include `raw_context_available_counts` or `exchange_context_summary`.

## No fabricated exchange context

Cannot be fully proven from this reused artifact set.

Reason:

- The synthetic dataset includes numeric exchange-context-like features such as `funding_rate`, `funding_rate_change`, `open_interest_change_pct`, and `premium_basis_rate`.
- It does not include raw context payloads, source summaries, source-error summaries, or missingness flags.
- Because this is a synthetic HMM/KNN audit dataset, those numeric values should be treated as synthetic features, not point-in-time exchange observations.

Finding:

- No evidence was found that the HMM/KNN parquet/csv outputs fabricate additional exchange context beyond the referenced dataset columns.
- The reused synthetic dataset itself does not carry enough raw context audit metadata to certify the no-fabrication exchange-context contract.

# Output consistency

Artifact path checks passed:

- Manifest paths exist for dataset, regime, KNN, meta, neighbor diagnostics, and metrics outputs.
- `walk_forward_metrics.json` reports `research_only: true`.
- `walk_forward_metrics.json` reports `promotion_ready: false`.
- Manifest `row_count` is `48`, matching the HMM/KNN output row count for `regime_posteriors.parquet`, `knn_predictions.parquet`, and `meta_predictions.parquet`.
- `neighbor_diagnostics.csv` has `4800` rows and is diagnostic-only.

# Final data finding

The reused generated artifact set is consistent for BTC-only HMM/KNN output auditing, but it is not a complete dataset-contract artifact.

Required follow-up before treating it as a full data-contract pass:

- Generate or reuse an artifact whose dataset was produced by `ResearchDatasetBuilder`.
- Ensure the dataset manifest includes `missing_feature_rates`, `raw_context_available_counts`, and `exchange_context_summary`.
- Ensure the dataset parquet includes raw context JSON/audit fields and `missing_*` columns for unavailable funding, OI, premium, and microstructure fields.
