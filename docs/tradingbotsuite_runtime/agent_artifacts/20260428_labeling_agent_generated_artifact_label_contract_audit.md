# Agent name

Labeling Agent

# Task received

Audit the same generated/reused artifact manifest and parquet/csv outputs for label contract consistency. Labeling checks: label outcome fields, realized cost fields, `label_exit_time_ms`, MFE/MAE, and no label columns in feature inputs. Write a separate artifact.

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
- `src/tradingbotsuite/research/dataset.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `tests/tradingbotsuite/test_hmm_knn.py`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_labeling_agent_generated_artifact_label_contract_audit.md`

# Commands/tests run

```powershell
Get-Content C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1\artifact_manifest.json
$env:PYTHONPATH='src'; python <artifact inspection script>
rg -n "LABEL_OUTCOME_COLUMNS|LabelOutcome|_label_from_future_bars|gross_return|fees_bps|slippage_bps|funding_paid_or_received|time_in_trade|max_adverse_excursion|max_favorable_excursion|barrier_hit_type|label_exit_time_ms|purge|embargo|feature_columns|label_column|pnl_column|meta_feature_columns|_leakage_safe" src\tradingbotsuite\research\dataset.py src\tradingbotsuite\research\hmm_knn.py tests\tradingbotsuite\test_hmm_knn.py tests\tradingbotsuite\test_research.py -S
```

The inspection script loaded the artifact manifest, referenced dataset parquet, all HMM/KNN parquet/csv outputs, and metrics JSON with pandas/json.

# Label contract summary

Manifest label metadata:

- `label_version`: `triple_barrier_live_parity_v1`
- `label_horizons`: `["6h", "24h", "72h", "7d"]`
- `primary_label_horizon`: `24h`
- `label_outcome_fields`:
  - `gross_return`
  - `fees_bps`
  - `slippage_bps`
  - `funding_paid_or_received`
  - `time_in_trade`
  - `max_adverse_excursion`
  - `max_favorable_excursion`
  - `barrier_hit_type`

The manifest advertises the expected label output contract.

# Dataset label fields

The referenced synthetic dataset parquet contains only the primary label fields:

- `label_accept`
- `label_pnl_multiple`
- `label_exit_reason`

Missing from the referenced dataset parquet:

- All manifest `label_outcome_fields`
- `label_exit_time_ms`
- `label_exit_price`
- `time_in_trade_bars`
- `realized_net_return_after_costs`

Finding:

- The reused synthetic dataset does not satisfy the full dataset label-outcome contract. It is sufficient for synthetic HMM/KNN smoke/audit runs, but not for validating full triple-barrier audit labels from `ResearchDatasetBuilder`.

# HMM/KNN meta artifact label fields

`meta_predictions.parquet` contains all manifest `label_outcome_fields`:

- `gross_return`: present, `0` nulls
- `fees_bps`: present, `0` nulls
- `slippage_bps`: present, `0` nulls
- `funding_paid_or_received`: present, `0` nulls
- `time_in_trade`: present, `48` nulls
- `max_adverse_excursion`: present, `48` nulls
- `max_favorable_excursion`: present, `48` nulls
- `barrier_hit_type`: present, `0` nulls

Interpretation:

- `gross_return`, cost fields, funding, and barrier type were backfilled by HMM/KNN preparation from the synthetic primary label fields and config.
- `time_in_trade`, MFE, and MAE remained null because the referenced dataset did not provide real label outcome values.

# Realized cost fields

Present and populated in `meta_predictions.parquet`:

- `gross_return`
- `fees_bps`
- `slippage_bps`
- `funding_paid_or_received`
- `realized_net_return_after_costs`

Observed numeric ranges:

- `fees_bps`: min `5.0`, max `5.0`
- `slippage_bps`: min `5.0`, max `5.0`
- `funding_paid_or_received`: min `-0.000030000000000000004`, max `0.000030000000000000004`
- `realized_net_return_after_costs`: min `-0.90103`, max `1.39903`

Metrics consistency:

- `walk_forward_metrics.json` reports `evaluation_basis.return_column: gross_return`.
- `walk_forward_metrics.json` reports `evaluation_basis.fee_bps: 5.0`.
- `walk_forward_metrics.json` reports `evaluation_basis.slippage_bps: 5.0`.
- `walk_forward_metrics.json` reports `evaluation_basis.funding_cost_enabled: true`.
- `walk_forward_metrics.json` reports `evaluation_basis.pnl_source: realized_label_return_after_fee_slippage_funding`.

# label_exit_time_ms, MFE, and MAE

Contract gap for the reused artifact set:

- `label_exit_time_ms` is absent from the referenced dataset parquet.
- `label_exit_time_ms` is absent from `meta_predictions.parquet`.
- `max_adverse_excursion` is present in `meta_predictions.parquet` but all `48` rows are null.
- `max_favorable_excursion` is present in `meta_predictions.parquet` but all `48` rows are null.
- `time_in_trade` is present in `meta_predictions.parquet` but all `48` rows are null.

Finding:

- The reused synthetic artifact set does not validate the full path-dependent label audit fields. It validates that HMM/KNN preserves/adds the public columns, but not that the columns contain real triple-barrier outcome values.
- A full label-contract pass requires a dataset generated after the Labeling Agent changes, where `label_exit_time_ms`, MFE, MAE, and `time_in_trade` are populated by `ResearchDatasetBuilder`.

# No label leakage into feature inputs

Pass.

The manifest feature columns do not overlap with label fields.

Observed collision set:

```text
[]
```

Label fields checked against feature inputs included:

- `label_accept`
- `label_pnl_multiple`
- `label_exit_reason`
- `label_exit_time_ms`
- `label_exit_price`
- all manifest `label_outcome_fields`
- `realized_net_return_after_costs`

Additional notes:

- `neighbor_diagnostics.csv` contains `neighbor_label_accept` and `neighbor_label_pnl_multiple`, but those are diagnostics for neighbor explainability, not manifest feature inputs.
- `knn_predictions.parquet` contains KNN outputs only and does not expose direct label columns.
- `meta_predictions.parquet` contains labels as evaluation outputs, while `meta_feature_columns` in code are limited to KNN outputs, HMM posterior fields, and configured feature columns.

# Purge/embargo implication

Because this reused synthetic dataset does not include `label_exit_time_ms`, the generated artifact cannot demonstrate label-exit-time purge behavior.

Code behavior remains:

- `_walk_forward_frames()` uses row embargo by default.
- When `label_exit_time_ms` is present, `_walk_forward_frames()` moves test start beyond the maximum train label exit time plus configured embargo.

Artifact finding:

- This specific reused artifact set used the fallback row-embargo path, not the full label-overlap purge path.

# Final labeling finding

The reused generated artifact set is label-feature-leakage safe and internally consistent for synthetic HMM/KNN output shape, costs, funding, barrier type, and metrics basis.

It is not a full label-contract pass because the referenced synthetic dataset lacks:

- `label_exit_time_ms`
- real `time_in_trade`
- real MFE/MAE values
- dataset-level label outcome fields

Required follow-up before treating artifacts as full Labeling Agent contract evidence:

- Generate or reuse a dataset produced by the updated `ResearchDatasetBuilder`.
- Run HMM/KNN research against that dataset.
- Re-audit that `meta_predictions.parquet` preserves populated `label_exit_time_ms`, `time_in_trade`, MFE, MAE, barrier type, costs, and funding fields.
