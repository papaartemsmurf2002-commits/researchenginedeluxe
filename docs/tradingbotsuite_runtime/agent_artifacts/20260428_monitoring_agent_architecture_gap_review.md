# Agent name

Monitoring Agent

# Task received

Assess whether monitoring alerts map to architecture risks.

# Files read

- `data/research/v2-btc-hmm-multi-knn-1/monitoring_report.json`
- `data/research/v2-btc-hmm-multi-knn-1/walk_forward_metrics.json`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_architecture_gap_review.md`

# Findings

Monitoring emitted observe-only warnings:

- `high_no_trade_rate`
- `low_neighbor_quality`

Useful diagnostic sections are present:

- feature outages: `0` high-outage features in the final artifact feature matrix
- entropy/no-trade: no-trade rate about `0.91`
- regime drift: max drift about `0.1996`
- neighbor quality: mean distance quality about `0.1555`
- funding costs: funding and expected net return fields present
- calibration decay: KNN and meta calibration buckets present

# Architecture gap

Monitoring correctly maps to the main architecture risks: defensive regime gating dominates, neighbor quality is weak, and meta output is not promotable. Alerts are advisory and observe-only.

# Open issues or blockers

None. Monitoring remains disconnected from live operator commands and live trading state.
