# Agent name

Execution/Risk Agent

# Task received

Rebuild include/exclude list for a focused HMM/KNN PR.

# Files read

- `git status -sb`
- `.gitignore`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_commit_scope_inventory.md`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_final_scope_review.md`

# Include for focused HMM/KNN package

- `configs/v2_btc_hmm_multi_knn_research.json`
- `src/tradingbotsuite/research/hmm_knn.py`
- `src/tradingbotsuite/research/hmm_knn_monitoring.py`
- research CLI and observe-only artifact display changes
- HMM/KNN runtime docs and agent artifacts
- HMM/KNN, research, and operator UI tests
- `.gitignore` rules excluding generated local content

# Exclude

- `tests/fixtures/btc_15m_fixture.json`
- `tradingbot/`
- `data/`
- virtualenvs, caches, logs, secrets, and generated local artifacts

# Boundary decision

Focused package scope remains research/docs/tests/observe-only. No live-boundary files should be staged unless a future explicitly approved live-promotion plan exists.
