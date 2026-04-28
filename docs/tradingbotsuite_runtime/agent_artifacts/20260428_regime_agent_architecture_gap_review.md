# Agent name

Regime Agent

# Task received

Assess whether real BTC regimes express the intended four-state architecture: range/chop, bull trend, bear trend, and shock/transition.

# Files read

- `data/research/v2-btc-hmm-multi-knn-1/regime_posteriors.parquet`
- `data/research/v2-btc-hmm-multi-knn-1/monitoring_report.json`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_regime_agent_architecture_gap_review.md`

# Findings

| Measure | Value |
| --- | ---: |
| Regime rows | `446` |
| Bear trend labels | `170` |
| Range/chop labels | `130` |
| Shock/transition labels | `77` |
| Bull trend labels | `69` |
| Mean posterior entropy | `0.23115281296041446` |
| P95 posterior entropy | `0.5350898796165469` |
| Mean max regime probability | `0.8713859425147195` |
| Regime no-trade rate | `0.9103139013452914` |
| Recent flip rate | `0.8946188340807175` |

# Architecture gap

All four intended labels appear in the real BTC artifact, so the state taxonomy did not collapse into a single regime. The main gap is stability: recent regime flips are extremely frequent and drive a very high no-trade rate. The regime layer is behaving more like a defensive uncertainty router than a stable market-state router.

# Recommended next experiment

Test less aggressive flip-cooldown/no-trade behavior and validate whether high flip rate is caused by feature noise, model fallback behavior, or insufficient training history. This remains research-only.
