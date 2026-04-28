# Agent name

Execution/Risk Agent

# Task received

Confirm real BTC evidence is still offline/research-only and no artifact is consumed by live code.

# Files read

- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/templates/research.html`
- `src/tradingbotsuite/research/hmm_knn.py`
- `src/tradingbotsuite/research/hmm_knn_monitoring.py`
- `data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_real_btc_evidence_boundary.md`

# Boundary findings

- Real BTC artifacts live under ignored `data/research/` and are not tracked source.
- `research-hmm-knn`, `replay-hmm-knn`, and `monitor-hmm-knn` are explicit research CLI commands.
- Operator research-page changes display observe-only artifact summaries.
- No live execution adapter, engine, runtime bootstrap, Control page, or operator command helper consumes HMM/KNN artifacts.
- Real BTC metrics remain `research_only: true` and `promotion_ready: false`.

# Decision

Real BTC evidence is offline, diagnostic, and non-promotable. It must not feed live gates, live sizing, Hyperliquid order placement, safety behavior, runtime-mode switching, or operator live controls.

# Open issues or blockers

None.
