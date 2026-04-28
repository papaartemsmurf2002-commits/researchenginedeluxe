# Agent name

KNN Agent

# Task received

Assess whether same-regime Lorentzian KNN is useful on real BTC artifacts.

# Files read

- `data/research/v2-btc-hmm-multi-knn-1/knn_predictions.parquet`
- `data/research/v2-btc-hmm-multi-knn-1/neighbor_diagnostics.csv`
- `data/research/v2-btc-hmm-multi-knn-1/walk_forward_metrics.json`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_architecture_gap_review.md`

# Findings

| Measure | Value |
| --- | ---: |
| Prediction rows | `446` |
| KNN accepted rate | `0.011210762331838564` |
| Accepted KNN trades | `5` |
| Neighbor count mean | `32.0` |
| Mean distance quality | `0.15553586717814147` |
| Diagnostic rows | `44600` |
| Cross-regime fallback used | `false` |
| Same-regime diagnostics | `100%` |

# Architecture gap

Same-regime enforcement works, K sweep fields are populated, and diagnostics are auditable. The useful-signal gap is large: accepted trades are too sparse, realized KNN expectancy is negative after costs, and distance quality is low. Current KNN output validates contract mechanics, not edge.

# Recommended next experiment

Focus on neighbor quality before tuning thresholds: extend real-data history, review regime pool size by state, and compare feature subsets with perp/microstructure completeness. Keep fallback disabled unless a separate experiment explicitly tests compatible-regime fallback.
