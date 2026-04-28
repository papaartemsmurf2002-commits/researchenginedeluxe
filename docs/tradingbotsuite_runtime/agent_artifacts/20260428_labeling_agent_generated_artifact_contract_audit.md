# Agent name

Labeling Agent

# Task received

Audit the same generated/reused artifact manifest and parquet/csv outputs for label contract consistency. Labeling checks label outcome fields, realized cost fields, `label_exit_time_ms`, MFE/MAE, and no label columns in feature inputs. Write a separate Labeling Agent artifact.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_labeling_agent_triple_barrier_audit.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_btc_dataset_point_in_time_audit.md`
- `data/research/v2-btc-research-1/dataset_manifest.json`
- `data/research/v2-btc-research-1/btcusdt_dataset.parquet`
- `data/research/v2-btc-research-1-btcusdt-artifacts/artifact_manifest.json`
- `data/research/v2-btc-research-1-btcusdt-artifacts/train_manifest.json`
- `data/research/v2-btc-research-1-btcusdt-artifacts/calibration.csv`
- `data/research/v2-btc-research-1-btcusdt-artifacts/rejected_vs_accepted.csv`
- `data/research/v2-btc-research-1-btcusdt-artifacts/metrics.json`
- `src/tradingbotsuite/research/dataset.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `src/tradingbotsuite/research/modeling.py`
- `src/tradingbotsuite/research/evaluation.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `tests/tradingbotsuite/test_research.py`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_labeling_agent_generated_artifact_contract_audit.md`

# Commands/tests run

```powershell
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_PROMPTS.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_ISSUES.md
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_labeling_agent_triple_barrier_audit.md
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_data_agent_btc_dataset_point_in_time_audit.md
Get-Content data\research\v2-btc-research-1\dataset_manifest.json
Get-Content data\research\v2-btc-research-1-btcusdt-artifacts\artifact_manifest.json
Get-Content data\research\v2-btc-research-1-btcusdt-artifacts\train_manifest.json
Get-Content data\research\v2-btc-research-1-btcusdt-artifacts\calibration.csv -TotalCount 5
Get-Content data\research\v2-btc-research-1-btcusdt-artifacts\rejected_vs_accepted.csv -TotalCount 5
Get-Content data\research\v2-btc-research-1-btcusdt-artifacts\metrics.json
python - <<audit script reading dataset parquet, manifests, and CSVs>>
rg -n "LABEL_OUTCOME_COLUMNS|label_outcome_fields|feature_columns|label_exit_time_ms|gross_return|fees_bps|slippage_bps|funding_paid_or_received|_prepare_dataset|_walk_forward_frames|meta_feature_columns|realized_net_return_after_costs" src\tradingbotsuite\research\dataset.py src\tradingbotsuite\research\hmm_knn.py src\tradingbotsuite\research\modeling.py src\tradingbotsuite\research\evaluation.py tests\tradingbotsuite\test_hmm_knn.py tests\tradingbotsuite\test_research.py
$env:PYTHONPATH="src"; python -m pytest tests\tradingbotsuite\test_research.py -q
$env:PYTHONPATH="src"; python -m pytest tests\tradingbotsuite\test_hmm_knn.py -q
```

Test results:

```text
tests\tradingbotsuite\test_research.py: 11 passed in 3.48s
tests\tradingbotsuite\test_hmm_knn.py: 19 passed in 5.64s
```

# Decisions made

- Treated this as a read-only artifact audit plus required artifact creation.
- Audited generated/reused outputs as they exist on disk, without regenerating or rewriting them.
- Separated generated artifact findings from current code behavior. Current code/test behavior supports the newer label outcome contract, but the generated/reused artifacts predate that contract.

# Audit results

## Dataset label fields

Generated dataset Parquet includes the legacy primary label fields:

- `label_accept`
- `label_pnl_multiple`
- `label_exit_reason`

Generated dataset Parquet is missing the current public label outcome fields:

- `gross_return`
- `fees_bps`
- `slippage_bps`
- `funding_paid_or_received`
- `time_in_trade`
- `max_adverse_excursion`
- `max_favorable_excursion`
- `barrier_hit_type`
- `label_exit_time_ms`
- `label_exit_price`

Generated `dataset_manifest.json` is also missing `label_outcome_fields`.

Finding: the generated dataset does not satisfy the current Labeling Agent output contract. It satisfies only the older `triple_barrier_live_parity_v1` primary label contract.

## Realized cost fields

Generated dataset Parquet does not include:

- `fees_bps`
- `slippage_bps`
- `funding_paid_or_received`
- `gross_return`
- `realized_net_return_after_costs`

The reused acceptance `metrics.json` reports cost-aware metrics using configured fee/slippage, but the generated dataset itself does not carry explicit realized cost fields.

Finding: downstream HMM/KNN code can backfill cost fields when missing, but these generated artifacts do not provide explicit realized cost columns for label audit.

## Exit time, MFE/MAE, and barrier type

Generated dataset Parquet does not include:

- `label_exit_time_ms`
- `time_in_trade`
- `time_in_trade_bars`
- `max_adverse_excursion`
- `max_favorable_excursion`
- `barrier_hit_type`

Generated CSV outputs:

- `rejected_vs_accepted.csv` columns: `signal_id`, `tv_bar_time_ms`, `accept_probability`, `accepted_by_model`, `label_accept`, `label_exit_reason`.
- `calibration.csv` columns: `confidence_bucket`, `row_count`, `mean_probability`, `mean_label`, `absolute_error`.

The CSVs do not include exit time, MFE/MAE, barrier type, realized cost fields, or full label outcome fields.

Finding: the generated/reused outputs are insufficient for current label-overlap, MFE/MAE, and barrier audit requirements.

## No label columns in feature inputs

The reused `artifact_manifest.json` feature list has `49` feature columns. None of these are label outcome columns.

Checked absent from feature inputs:

- `label_accept`
- `label_pnl_multiple`
- `label_exit_reason`
- `gross_return`
- `fees_bps`
- `slippage_bps`
- `funding_paid_or_received`
- `time_in_trade`
- `max_adverse_excursion`
- `max_favorable_excursion`
- `barrier_hit_type`
- `label_exit_time_ms`
- `label_exit_price`

All feature columns listed in the reused artifact manifest exist in the dataset Parquet.

Finding: the reused artifact passes the "no label columns in feature inputs" check.

## Manifest consistency

The reused downstream manifests are stale relative to the generated dataset:

- `artifact_manifest.json` total rows: `1194`
- actual dataset rows: `1173`
- `artifact_manifest.json` feature version: `v2-btc-acceptance-1`
- dataset manifest feature version: `v2-btc-acceptance-2`

Finding: do not rely on `data/research/v2-btc-research-1-btcusdt-artifacts/` as current evidence for label contract consistency. It should be regenerated after the dataset is rebuilt.

## Current code contract check

Current code paths support the current label contract:

- `dataset.py` defines `LABEL_OUTCOME_COLUMNS` and writes label outcome fields when rebuilding datasets.
- `hmm_knn.py` preserves real dataset outcome fields when present and backfills only when older datasets lack them.
- `_walk_forward_frames()` uses `label_exit_time_ms` for purge when available.
- HMM/KNN artifact manifests include `label_outcome_fields` when generated from current code.

Tests passed for the current code contract:

- `tests/tradingbotsuite/test_research.py`: `11 passed`
- `tests/tradingbotsuite/test_hmm_knn.py`: `19 passed`

# Assumptions

- "Same generated/reused artifact" means the existing files under `data/research/v2-btc-research-1/` and `data/research/v2-btc-research-1-btcusdt-artifacts/`.
- No generated HMM/KNN parquet/csv outputs were present under `data/research`; this audit covers the legacy dataset Parquet and reused V2 acceptance CSVs/manifests.
- Existing dirty/untracked files belong to the active multi-agent HMM/KNN workstream and should not be reverted.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues before this audit, and no new issue was appended.

# Handoff notes for other agents

- Regenerate the BTC dataset before treating it as current Labeling Agent evidence. The on-disk Parquet lacks current label outcome fields.
- Regenerate downstream artifacts after dataset regeneration. The existing reused model artifacts are stale in row count and feature version.
- Until regenerated, these artifacts prove only that legacy feature inputs avoided label columns and that legacy labels had `label_accept`, `label_pnl_multiple`, and `label_exit_reason`.
- HMM/KNN agents should prefer freshly generated artifacts from current code so `label_exit_time_ms`, MFE/MAE, realized cost fields, and manifest `label_outcome_fields` are present.
