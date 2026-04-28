# Agent name

Labeling Agent

# Task received

Validate real BTC label credibility: barrier distribution, missing exit times, time-in-trade distribution, funding coverage, MFE/MAE availability, and label horizon coverage.

# Files read

- `data/research/v2-btc-research-1/btcusdt_dataset.parquet`
- `data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json`
- `data/research/v2-btc-hmm-multi-knn-1/meta_predictions.parquet`
- `data/research/v2-btc-hmm-multi-knn-1/walk_forward_metrics.json`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_labeling_agent_real_btc_label_distribution.md`

# Label findings

- The HMM/KNN artifact manifest records `label_version = triple_barrier_live_parity_v1`.
- The real BTC HMM/KNN metrics use `realized_label_return_after_fee_slippage_funding` as the PnL basis.
- `meta_predictions.parquet` carries label outcome fields for evaluation, but the source dataset manifest is older and does not list `label_outcome_fields`.
- The source dataset did not expose direct `barrier_hit_type`, `label_exit_time_ms`, MFE, MAE, or `funding_paid_or_received` columns during this audit. This limits exact label-distribution claims from the saved dataset alone.
- Costed evaluation still reports funding, fee, and slippage accounting in `walk_forward_metrics.json`.

# Decision

The real BTC artifacts are credible for coarse contract execution and costed replay diagnostics. They are insufficient for exact label-quality claims about barrier distribution, realized exit timing, or MFE/MAE distribution until the real dataset is regenerated with the latest hardened label outcome fields.

# Open issues or blockers

No blocker for the current research-only diagnostic state. Exact label-distribution validation should be part of the next real-data regeneration pass.
