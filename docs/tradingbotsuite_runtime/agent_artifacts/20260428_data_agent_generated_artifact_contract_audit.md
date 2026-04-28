# Agent name

Data Agent

# Task received

Audit the same generated/reused artifact manifest and parquet/csv outputs for dataset contract consistency. Data checks BTC-only scope, missingness fields, raw context summaries, and no fabricated exchange context. Write a separate Data Agent artifact.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_btc_dataset_point_in_time_audit.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_labeling_agent_triple_barrier_audit.md`
- `data/research/v2-btc-research-1/dataset_manifest.json`
- `data/research/v2-btc-research-1/btcusdt_dataset.parquet`
- `data/research/v2-btc-research-1-btcusdt-artifacts/artifact_manifest.json`
- `data/research/v2-btc-research-1-btcusdt-artifacts/train_manifest.json`
- `data/research/v2-btc-research-1-btcusdt-artifacts/calibration.csv`
- `data/research/v2-btc-research-1-btcusdt-artifacts/rejected_vs_accepted.csv`
- `data/research/v2-btc-research-1-btcusdt-artifacts/metrics.json`
- `src/tradingbotsuite/research/dataset.py`
- `src/tradingbotsuite/adapters/binance.py`
- `tests/tradingbotsuite/test_research.py`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_generated_artifact_contract_audit.md`

# Commands/tests run

```powershell
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_PROMPTS.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_ISSUES.md
Get-ChildItem docs\tradingbotsuite_runtime\agent_artifacts -Force
Get-ChildItem data\research -Recurse -File | Select-Object FullName,Length,LastWriteTime
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_data_agent_btc_dataset_point_in_time_audit.md
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_labeling_agent_triple_barrier_audit.md
Get-Content data\research\v2-btc-research-1\dataset_manifest.json
Get-Content data\research\v2-btc-research-1-btcusdt-artifacts\artifact_manifest.json
Get-Content data\research\v2-btc-research-1-btcusdt-artifacts\train_manifest.json
Get-Content data\research\v2-btc-research-1-btcusdt-artifacts\calibration.csv -TotalCount 5
Get-Content data\research\v2-btc-research-1-btcusdt-artifacts\rejected_vs_accepted.csv -TotalCount 5
Get-Content data\research\v2-btc-research-1-btcusdt-artifacts\metrics.json
Get-ChildItem data\research\v2-btc-research-1,data\research\v2-btc-research-1-btcusdt-artifacts -File | Format-Table Name,Length,LastWriteTime -AutoSize
python - <<audit script reading dataset parquet, manifests, and CSVs>>
rg -n "fetch_funding_context|fetch_open_interest_context|fetch_premium_context|current_payload|abs\(now_ms - as_of_ms\)|endTime" src\tradingbotsuite\adapters\binance.py
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
- Audited the generated dataset artifact at `data/research/v2-btc-research-1/` and the reused downstream acceptance artifacts at `data/research/v2-btc-research-1-btcusdt-artifacts/`.
- Did not regenerate the dataset or downstream artifacts. The findings below distinguish the current code contract from the existing generated/reused artifact state.
- Did not append an issue because no clarification blocker was encountered; the stale artifact findings are actionable without guessing.

# Audit results

## BTC-only scope

- Dataset Parquet shape: `1173` rows x `105` columns.
- Dataset manifest `symbol`: `BTCUSDT`.
- Dataset Parquet unique symbols: `BTCUSDT` only.
- Dataset manifest row count matches actual Parquet row count: `1173`.
- Current generated dataset passes BTC-only scope.

## Dataset manifest consistency

- `dataset_manifest.json` points to `data\research\v2-btc-research-1\btcusdt_dataset.parquet`.
- `dataset_manifest.json` row count matches the Parquet.
- `dataset_manifest.json` is stale against the current Data Agent manifest contract. Missing current required keys:
  - `research_only`
  - `asset_scope`
  - `label_outcome_fields`
  - `raw_context_available_counts`
  - `exchange_context_summary`
- The reused downstream `artifact_manifest.json` is stale against the dataset:
  - artifact `total_rows`: `1194`
  - dataset actual rows: `1173`
  - artifact `feature_version`: `v2-btc-acceptance-1`
  - dataset manifest `feature_version`: `v2-btc-acceptance-2`
- Handoff decision: do not use `data/research/v2-btc-research-1-btcusdt-artifacts/artifact_manifest.json` as a current contract witness without retraining/regenerating it from the current dataset.

## Missingness fields

Required legacy missingness fields are present in the dataset for funding, OI, premium, and microstructure. Observed selected missing rates:

- `missing_funding_rate`: `0.0`
- `missing_open_interest`: `0.8746803069053708`
- `missing_premium_basis_rate`: `1.0`
- `missing_premium_close`: `0.0`
- `missing_primary_signed_imbalance_ratio`: `1.0`
- `missing_spread_bps`: `1.0`

Interpretation:

- Funding and premium close are present for all rows.
- OI is mostly unavailable: `1026` missing rows and `147` observed rows.
- Premium basis and captured microstructure are fully missing in this generated dataset.
- The missingness flags make those outages explicit.

## Raw context summaries

Current Data Agent contract expects raw audit fields and manifest summaries. The generated dataset predates that contract.

Missing from the generated dataset:

- Signal-bar OHLCV audit fields: `signal_bar_open_time_ms`, `signal_bar_close_time_ms`, `signal_bar_open`, `signal_bar_high`, `signal_bar_low`, `signal_bar_close`, `signal_bar_volume`.
- Point-in-time audit window fields: `historical_feature_end_time_ms`, `label_future_start_time_ms`, `label_future_end_time_ms`, `label_future_bar_count`.
- Raw exchange fields: `raw_funding_rate`, `raw_funding_rate_change`, `raw_open_interest`, `raw_open_interest_change`, `raw_open_interest_change_pct`, `raw_open_interest_value`, `raw_premium_basis_rate`, `raw_premium_basis_abs`, `raw_premium_close`, `raw_mark_price`, `raw_index_price`.
- Raw context JSON fields: `funding_context_json`, `open_interest_context_json`, `premium_context_json`, `microstructure_context_json`, `basis_context_json`.

Missing from the generated dataset manifest:

- `raw_context_available_counts`
- `exchange_context_summary`

Finding: the generated dataset cannot satisfy the current raw-context-summary audit requirement until `build-dataset` is rerun with the current builder.

## No fabricated exchange context

Legacy normalized field checks found no nonzero fabricated values where missingness flags indicate unavailable context:

- `open_interest`, `open_interest_change`, `open_interest_change_pct`, and `open_interest_value`: `1026` missing rows each, `0` nonzero values when missing, and `0` nulls when observed.
- `premium_basis_rate` and `premium_basis_abs`: `1173` missing rows each, `0` nonzero values when missing.
- `funding_rate`, `funding_rate_change`, and `premium_close`: no missing rows.

Finding: the generated dataset passes the legacy no-fabricated-normalized-values check, but lacks the newer raw-null audit fields needed for stronger provenance validation.

# Assumptions

- "Same generated/reused artifact" means the existing files under `data/research/v2-btc-research-1/` and `data/research/v2-btc-research-1-btcusdt-artifacts/`.
- No HMM/KNN generated Parquet or CSV outputs were present under `data/research`; only the BTC dataset Parquet and reused V2 acceptance CSVs were audited.
- Existing dirty/untracked files belong to the active multi-agent HMM/KNN workstream and should not be reverted.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues before this audit, and no new issue was appended.

# Handoff notes for other agents

- Regenerate `data/research/v2-btc-research-1/btcusdt_dataset.parquet` and `dataset_manifest.json` with the current `ResearchDatasetBuilder` before using the dataset as a current Data Agent contract artifact.
- Retrain/regenerate `data/research/v2-btc-research-1-btcusdt-artifacts/` after dataset regeneration. The existing downstream manifest has stale row count and feature-version metadata.
- Until regenerated, the generated dataset is usable only as a legacy BTC-only dataset with explicit normalized missingness flags, not as a current raw-context audit artifact.
