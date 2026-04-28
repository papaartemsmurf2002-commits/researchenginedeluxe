# Agent name

Data Agent

# Task received

Validate real BTC dataset lineage: source path, row count, time span, missingness, raw context availability, and whether funding/OI/premium fields are observed or placeholders.

# Files read

- `data/research/v2-btc-research-1/btcusdt_dataset.parquet`
- `data/research/v2-btc-research-1/dataset_manifest.json`
- `data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_real_btc_lineage_quality.md`

# Lineage summary

| Field | Value |
| --- | --- |
| Dataset path | `data/research/v2-btc-research-1/btcusdt_dataset.parquet` |
| Dataset rows | `1173` |
| Dataset columns | `105` |
| Symbol | `BTCUSDT` |
| Dataset feature version | `v2-btc-acceptance-2` |
| HMM/KNN plan version | `v2-btc-hmm-multi-knn-1` |
| HMM/KNN evaluation rows | `446` |

# Data quality findings

- Funding fields are present and not missing in the dataset feature map.
- Open-interest fields are mostly missing: `missing_open_interest`, `missing_open_interest_change`, `missing_open_interest_change_pct`, and `missing_open_interest_value` are about `0.87468`.
- Premium close is present, but `premium_basis_rate`, `premium_basis_abs`, and `basis_bps` are fully missing or placeholder-level in the dataset manifest.
- Microstructure/order-book features such as signed imbalance, queue imbalance, top-of-book imbalance, and spread are fully missing in this real BTC dataset.
- The saved dataset manifest does not expose the newer `raw_context_available_counts`, `exchange_context_summary`, `asset_scope`, or `label_outcome_fields` fields. That means this dataset is usable for coarse replay and artifact generation, but weaker than the current hardened dataset contract.

# Decision

The dataset is usable for local Phase 1 diagnostic artifact generation. It is not strong enough for production-quality edge claims because important perp/microstructure context is missing or mostly unavailable.

# Open issues or blockers

None for diagnostics. A future real-data validation pass should regenerate the dataset with the latest hardened manifest contract if exact raw context availability is required.
