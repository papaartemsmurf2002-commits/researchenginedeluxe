# Agent name

Meta-Model Agent

# Task received

Objective: evaluate real-data meta-filter behavior.

Tasks:

- Inspect `meta_predictions.parquet` and `walk_forward_metrics.json`.
- Report backend, class diversity, trade count, meta vs pure KNN comparison, and failure reasons.
- Explicitly state whether meta output is contract-only or analytically useful.
- Write artifact: `docs/tradingbotsuite_runtime/agent_artifacts/20260428_meta_model_agent_real_btc_meta_review.md`.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_real_btc_runbook.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_real_btc_dataset_inventory.md`
- `data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json`
- `data/research/v2-btc-hmm-multi-knn-1/walk_forward_metrics.json`
- `data/research/v2-btc-hmm-multi-knn-1/meta_predictions.parquet`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_meta_model_agent_real_btc_meta_review.md`

# Commands/tests run

```powershell
Get-Content -Raw 'docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_PROMPTS.md'
Get-Content -Raw 'docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_ISSUES.md'
Get-ChildItem -Force 'data\research\v2-btc-hmm-multi-knn-1' | Select-Object Mode,Length,LastWriteTime,Name
```

Observed the expected real BTC HMM/KNN artifact set:

- `artifact_manifest.json`
- `knn_predictions.parquet`
- `meta_predictions.parquet`
- `monitoring_report.json`
- `neighbor_diagnostics.csv`
- `regime_posteriors.parquet`
- `walk_forward_metrics.json`

```powershell
$env:PYTHONPATH='src'; python <inspection script reading artifact_manifest.json, walk_forward_metrics.json, and meta_predictions.parquet>
```

Inspection summary:

```json
{
  "artifact_dir": "data\\research\\v2-btc-hmm-multi-knn-1",
  "manifest_research_only": true,
  "metrics_research_only": true,
  "metrics_promotion_ready": false,
  "meta_rows": 446,
  "meta_backend_values": ["random_forest_fallback"],
  "meta_backend_counts": {"random_forest_fallback": 446},
  "manifest_dependencies": {
    "hmm_backend": ["gaussian_mixture_fallback"],
    "hmmlearn_available": false,
    "meta_backend": ["random_forest_fallback"],
    "xgboost_available": false
  },
  "label_accept_counts": {"0": 282, "1": 164},
  "accepted_by_knn_count": 5,
  "accepted_by_meta_count": 0,
  "accepted_by_meta_and_knn_count": 0
}
```

No pytest command was run for this read-only artifact inspection. Previous focused HMM/KNN regression coverage was already recorded separately in `20260428_meta_model_agent_backend_regression_hardening.md`.

# Decisions made

- Selected `data/research/v2-btc-hmm-multi-knn-1` as the real BTC HMM/KNN artifact because the Data Agent identified `data/research/v2-btc-research-1/btcusdt_dataset.parquet` as the usable local BTC dataset and the Backtest Agent runbook names this output directory as the expected real-data HMM/KNN destination.
- Treated the inspected result as research-only. The metrics explicitly report `research_only: true` and `promotion_ready: false`.
- Classified the backend state as fallback-only:
  - `artifact_manifest.json` reports `dependencies.xgboost_available: false`.
  - `artifact_manifest.json` reports `dependencies.meta_backend: ["random_forest_fallback"]`.
  - Every row in `meta_predictions.parquet` reports `meta_model_backend = random_forest_fallback`.
- Confirmed class diversity exists in the meta output and training summaries:
  - Output labels: `282` negative and `164` positive `label_accept` rows.
  - Meta validation training summaries report `label_class_count: 2` for all three evaluated training windows.
  - Training label counts by split were `492/211`, `592/275`, and `701/330` negative/positive.
- Confirmed pure KNN and meta-filter are compared on realized post-cost outcomes, not only expected-value estimates:
  - Both comparison branches use `pnl_source: realized_label_return_after_fee_slippage_funding`.
  - Both include `fee_bps: 5.0`, `slippage_bps: 5.0`, and `funding_cost_enabled: true`.

# Real-data meta comparison

Pure HMM-routed Lorentzian KNN:

- `trade_count`: `5`
- `accepted_rate`: `0.011210762331838564`
- `no_trade_rate`: `0.9887892376681614`
- `long_count`: `3`
- `short_count`: `2`
- `expectancy_after_cost`: `-1.0008811453163364`
- `expected_value_mean`: `0.5369863511187972`
- `gross_return_mean`: `-0.9998211453163364`
- `funding_paid_or_received_mean`: `-0.00006000000000000001`
- `realized_pnl_total`: `-5.004405726581682`
- `profit_factor`: `0.0`
- `tp_before_sl_rate`: `0.0`

HMM/KNN meta-filter:

- `trade_count`: `0`
- `accepted_rate`: `0.0`
- `no_trade_rate`: `1.0`
- `long_count`: `0`
- `short_count`: `0`
- `expectancy_after_cost`: `0.0`
- `expected_value_mean`: `null`
- `gross_return_mean`: `null`
- `funding_paid_or_received_mean`: `null`
- `realized_pnl_total`: `0.0`
- `profit_factor`: `null`
- `tp_before_sl_rate`: `0.0`

# Failure reasons

`meta_validation.failure_reasons` is empty for the real run because the meta training windows had two classes and enough rows to fit the fallback model.

Promotion failure reporting is explicit in `walk_forward_metrics.json`:

- `knn_expectancy_after_cost_below_threshold`
- `knn_insufficient_trade_count`
- `knn_single_split_dominates_pnl`
- `meta_insufficient_trade_count`
- `meta_missing_long_short_breakout`
- `research_only_not_live_promotable`

# Analytical usefulness

The real BTC meta output is contract-valid and diagnostically useful, but it is not analytically useful for performance or edge claims.

Rationale:

- Backend recording is clear and complete, but the run used `random_forest_fallback`, not XGBoost.
- Meta labels have two-class diversity, so this is not a one-class training failure.
- The meta-filter accepted zero trades, so it has no realized meta trade sample to analyze.
- Pure KNN accepted only five trades and produced negative realized post-cost expectancy.
- Promotion failures explicitly flag insufficient KNN/meta trade counts, single-split PnL concentration, missing meta long/short breakout, and research-only non-promotability.

Conclusion: use this artifact to validate the research contract, fallback reporting, realized comparison fields, and explicit failure reporting. Do not use it to claim statistical edge, live readiness, or model improvement.

# Assumptions

- `data/research/v2-btc-hmm-multi-knn-1` is the intended real BTC HMM/KNN output for this review.
- The real dataset provenance caveat from `20260428_data_agent_real_btc_dataset_inventory.md` still applies: the source dataset is consumable by HMM/KNN, but stale relative to the latest raw-context manifest contract.
- No live trading behavior, sizing, Hyperliquid execution, safety behavior, or operator live controls were in scope.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues. No new issue was appended.

# Handoff notes for other agents

- Future analytical evaluation needs a larger, current, point-in-time BTC dataset that clears raw-context provenance requirements and yields enough accepted trades across multiple splits.
- The current real run confirms failure reporting is doing useful work: weak pure KNN behavior and zero accepted meta trades are visible rather than hidden.
- Keep this artifact out of promotion materials. It is a research-contract and negative/diagnostic evidence artifact, not a performance scorecard.
