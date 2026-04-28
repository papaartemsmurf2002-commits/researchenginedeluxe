# Agent name

Backtest Agent

# Task received

Run real BTC research if Data Agent found a usable dataset.

Requested commands:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main research-hmm-knn --config configs/v2_btc_hmm_multi_knn_research.json --dataset <DATASET_PATH> --output-dir data/research
$env:PYTHONPATH='src'; python -m tradingbotsuite.main monitor-hmm-knn --manifest <ARTIFACT_MANIFEST_PATH>
$env:PYTHONPATH='src'; python -m pytest -q
```

If no dataset exists, do not fake it; write "blocked by missing real BTC dataset". If dataset exists, run and record artifact paths. Report high-level metrics only, no live-readiness claim.

# Files read

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_real_btc_dataset_inventory.md`
- `data/research/v2-btc-research-1/dataset_manifest.json`
- `data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json`
- `data/research/v2-btc-hmm-multi-knn-1/walk_forward_metrics.json`
- `data/research/v2-btc-hmm-multi-knn-1/monitoring_report.json`

# Files changed

- `data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json`
- `data/research/v2-btc-hmm-multi-knn-1/walk_forward_metrics.json`
- `data/research/v2-btc-hmm-multi-knn-1/regime_posteriors.parquet`
- `data/research/v2-btc-hmm-multi-knn-1/knn_predictions.parquet`
- `data/research/v2-btc-hmm-multi-knn-1/meta_predictions.parquet`
- `data/research/v2-btc-hmm-multi-knn-1/neighbor_diagnostics.csv`
- `data/research/v2-btc-hmm-multi-knn-1/monitoring_report.json`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_real_btc_contract_run.md`

# Dataset decision

Data Agent identified a usable local no-fetch BTC dataset for HMM/KNN artifact generation:

```text
data/research/v2-btc-research-1/btcusdt_dataset.parquet
```

Important caveat from `20260428_data_agent_real_btc_dataset_inventory.md`: this is a schema-compatible legacy BTC dataset, not a fully current Data Agent raw-context artifact. Its manifest/parquet predate the newest raw-context audit fields. I used it because Data Agent explicitly recommended it when a local no-fetch BTC dataset is needed for HMM/KNN artifact generation.

No live exchange data was fetched or used.

# Commands/tests run

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main research-hmm-knn --config configs/v2_btc_hmm_multi_knn_research.json --dataset data/research/v2-btc-research-1/btcusdt_dataset.parquet --output-dir data/research
```

Exit code: `0`

Exact output:

```json
{
  "output_dir": "data\\research\\v2-btc-hmm-multi-knn-1",
  "artifact_manifest_path": "data\\research\\v2-btc-hmm-multi-knn-1\\artifact_manifest.json",
  "metrics_path": "data\\research\\v2-btc-hmm-multi-knn-1\\walk_forward_metrics.json",
  "regime_posteriors_path": "data\\research\\v2-btc-hmm-multi-knn-1\\regime_posteriors.parquet",
  "knn_predictions_path": "data\\research\\v2-btc-hmm-multi-knn-1\\knn_predictions.parquet",
  "meta_predictions_path": "data\\research\\v2-btc-hmm-multi-knn-1\\meta_predictions.parquet",
  "neighbor_diagnostics_path": "data\\research\\v2-btc-hmm-multi-knn-1\\neighbor_diagnostics.csv"
}
```

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main monitor-hmm-knn --manifest data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json
```

Exit code: `0`

Exact output:

```json
{
  "monitoring_report_path": "data\\research\\v2-btc-hmm-multi-knn-1\\monitoring_report.json"
}
```

```powershell
$env:PYTHONPATH='src'; python -m pytest -q
```

Exit code: `0`

Exact result:

```text
........................................................................ [ 18%]
........................................................................ [ 37%]
........................................................................ [ 56%]
........................................................................ [ 75%]
........................................................................ [ 93%]
.......................                                                  [100%]
383 passed in 145.74s (0:02:25)
```

# Artifact paths

- Output directory: `data/research/v2-btc-hmm-multi-knn-1`
- Manifest: `data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json`
- Metrics: `data/research/v2-btc-hmm-multi-knn-1/walk_forward_metrics.json`
- Regime posteriors: `data/research/v2-btc-hmm-multi-knn-1/regime_posteriors.parquet`
- KNN predictions: `data/research/v2-btc-hmm-multi-knn-1/knn_predictions.parquet`
- Meta predictions: `data/research/v2-btc-hmm-multi-knn-1/meta_predictions.parquet`
- Neighbor diagnostics: `data/research/v2-btc-hmm-multi-knn-1/neighbor_diagnostics.csv`
- Monitoring report: `data/research/v2-btc-hmm-multi-knn-1/monitoring_report.json`

# High-level metrics only

Manifest:

- Plan version: `v2-btc-hmm-multi-knn-1`
- Symbol: `BTCUSDT`
- Dataset path: `data\research\v2-btc-research-1\btcusdt_dataset.parquet`
- Row count: `446`
- Research only: `true`
- HMM backend: `gaussian_mixture_fallback`
- Meta backend: `random_forest_fallback`
- `hmmlearn_available`: `false`
- `xgboost_available`: `false`

Overall metrics:

- `research_only`: `true`
- `promotion_ready`: `false`
- Evaluation row count: `446`
- Positive split ratio: `0.0`
- Max single split PnL share: `0.0`
- Promotion failures:
  - `knn_expectancy_after_cost_below_threshold`
  - `knn_insufficient_trade_count`
  - `knn_single_split_dominates_pnl`
  - `meta_insufficient_trade_count`
  - `meta_missing_long_short_breakout`
  - `research_only_not_live_promotable`

Pure KNN comparison:

- Trade count: `5`
- Long count: `3`
- Short count: `2`
- Accepted rate: `0.011210762331838564`
- No-trade rate: `0.9887892376681614`
- Expectancy after cost: `-1.0008811453163364`
- Realized PnL total: `-5.004405726581682`
- Profit factor: `0.0`
- Expected value mean: `0.5369863511187972`
- PnL source: `realized_label_return_after_fee_slippage_funding`

Meta-filter comparison:

- Trade count: `0`
- Long count: `0`
- Short count: `0`
- Accepted rate: `0.0`
- No-trade rate: `1.0`
- Expectancy after cost: `0.0`
- Realized PnL total: `0.0`
- Profit factor: `null`
- PnL source: `realized_label_return_after_fee_slippage_funding`

Monitoring:

- `research_only`: `true`
- `observe_only`: `true`
- `promotion_ready`: `false`
- `live_vs_replay_mismatch`: `not_available`
- Alerts:
  - `high_no_trade_rate`, observe-only warning
  - `low_neighbor_quality`, observe-only warning

# Live-readiness statement

No live-readiness claim exists from this run.

No positive expectancy claim exists from this run. Pure KNN costed expectancy was negative, the meta-filter accepted zero trades, and `promotion_ready` remained `false`.

This run is a research-contract run on a local legacy BTC dataset only. It does not approve live execution, live sizing, live gates, Hyperliquid behavior, safety behavior, or operator live controls.

# Decisions made

- Used the Data Agent identified local dataset instead of fabricating or generating synthetic data.
- Did not fetch live exchange data.
- Ran monitoring only after a successful local research artifact was produced.
- Reported high-level metrics only and avoided performance or live-readiness claims.

# Assumptions

- Data Agent's "usable for HMM/KNN artifact generation" recommendation is sufficient authorization to run this Backtest contract pass despite the stale raw-context manifest caveat.
- The generated artifact path under `data/research/v2-btc-hmm-multi-knn-1` is acceptable for this real local dataset contract run.

# Open issues or blockers

None for artifact generation.

Research caveat: the input dataset should be regenerated before any stricter current Data Agent raw-context audit or performance claim.

# Handoff notes for other agents

- The real local BTC command path works end-to-end with the identified dataset.
- The generated artifacts are non-promotional and research-only.
- Next Backtest work should focus on a regenerated current-contract BTC dataset and a deeper metrics review once trade counts, split coverage, and data freshness are adequate.
