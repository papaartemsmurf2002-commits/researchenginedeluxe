# Agent name

Backtest Agent

# Task received

Read the latest real BTC HMM/KNN artifacts under `data/research/v2-btc-hmm-multi-knn-1` and produce a compact acceptance evidence table.

# Files read

- `data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json`
- `data/research/v2-btc-hmm-multi-knn-1/walk_forward_metrics.json`
- `data/research/v2-btc-hmm-multi-knn-1/monitoring_report.json`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_real_btc_evidence_summary.md`

# Evidence table

| Gate | Real BTC result | Status |
| --- | ---: | --- |
| Research-only flag | `true` | pass |
| Promotion ready | `false` | pass, non-promotable |
| Evaluation rows | `446` | diagnostic only |
| Pure KNN trades | `5` | fail, below `25` minimum |
| Meta trades | `0` | fail |
| Pure KNN expectancy after cost | `-1.0008811453163364` | fail |
| Pure KNN realized PnL total | `-5.004405726581682` | fail |
| Pure KNN accepted rate | `0.011210762331838564` | too sparse |
| Meta accepted rate | `0.0` | fail |
| Positive split ratio | `0.0` | fail |
| Long/short breakout | KNN `3` long, `2` short; meta `0`/`0` | fail for meta |
| Regime no-trade rate | `0.9103139013452914` | warning |
| Neighbor distance quality mean | `0.15553586717814147` | warning |

# Promotion failures

- `knn_expectancy_after_cost_below_threshold`
- `knn_insufficient_trade_count`
- `knn_single_split_dominates_pnl`
- `meta_insufficient_trade_count`
- `meta_missing_long_short_breakout`
- `research_only_not_live_promotable`

# Decision

The real BTC run is useful diagnostic evidence, but it fails acceptance. It does not support profitability, live readiness, or any promotion into live gates, sizing, execution, Hyperliquid behavior, safety behavior, or operator live controls.

# Open issues or blockers

None. The evidence is negative but interpretable; no clarification issue is required.
