# Agent name

Monitoring Agent

# Task received

Verify monitoring still reads hardened artifacts and remains observe-only.

Required commands:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py tests/tradingbotsuite/test_hmm_knn.py::test_hmm_knn_monitoring_report_is_research_only_and_observe_only -q
rg -n "monitoring_report|observe_only|promotion_ready|feature_outage|neighbor_quality|regime_distribution_drift" src tests docs/tradingbotsuite_runtime
```

Also verify monitoring handles any new or clarified artifact fields without requiring live state, add or verify a test that missing required artifact files fail clearly, and write this artifact.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `src/tradingbotsuite/research/hmm_knn_monitoring.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `tests/tradingbotsuite/test_operator_ui.py`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/templates/research.html`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_SOURCE_LOG.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_RUNBOOK.md`
- Prior monitoring handoffs under `docs/tradingbotsuite_runtime/agent_artifacts/`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_hardened_artifact_followup.md`

# Commands/tests run

Requested pytest command:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py tests/tradingbotsuite/test_hmm_knn.py::test_hmm_knn_monitoring_report_is_research_only_and_observe_only -q
```

Exact result:

```text
......................                                                   [100%]
22 passed in 8.43s
```

Requested search command:

```powershell
rg -n "monitoring_report|observe_only|promotion_ready|feature_outage|neighbor_quality|regime_distribution_drift" src tests docs/tradingbotsuite_runtime
```

Result summary:

- `src/tradingbotsuite/research/hmm_knn_monitoring.py` still writes `monitoring_report.json` with `research_only: true`, `observe_only: true`, and `promotion_ready: false`.
- Monitoring still emits observe-only alerts for `feature_outage`, `regime_distribution_drift`, and `low_neighbor_quality`.
- `tests/tradingbotsuite/test_hmm_knn.py::test_hmm_knn_monitoring_report_is_research_only_and_observe_only` asserts the observe-only flags and major report sections.
- `tests/tradingbotsuite/test_operator_ui.py` asserts HMM/KNN monitoring summaries render as observe-only research artifacts.
- Runtime docs and prior artifacts document the same observe-only monitoring contract.

Missing required artifact file check:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py::test_hmm_knn_monitoring_fails_clearly_when_required_artifact_is_missing -q
```

Exact result:

```text
.                                                                        [100%]
1 passed in 2.07s
```

# Decisions made

- Verified the existing missing-file test instead of adding a duplicate test. The current test deletes `neighbor_diagnostics.csv` from a generated HMM/KNN artifact and asserts `monitor_hmm_knn_artifact` raises `FileNotFoundError` matching `missing required artifact files`.
- Confirmed monitoring handles hardened artifact fields as passive artifact metadata: it reads the manifest and artifact paths, preserves identity fields such as manifest version, plan version/hash, symbol, asset scope, config path, dataset path, and row count, and does not require engine state, operator command state, Hyperliquid state, safe-mode state, or live runtime state.
- Confirmed clarified artifact fields do not force live coupling. Optional config is read only when present; missing config returns `{}`. Calibration/funding/regime/neighbor sections degrade from available artifact columns rather than live services.
- No source code changes were needed for this follow-up.

# Assumptions

- "Hardened artifacts" refers to the current HMM/KNN artifact contract with manifest identity fields, output paths, feature/version metadata, metrics, diagnostics, and observe-only monitoring output.
- The `rg` command output is large; this artifact records the relevant matches and conclusions rather than copying every line.
- Verifying the existing missing-file test satisfies "Add or verify a test" because it directly covers the required failure mode.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues.

# Handoff notes for other agents

- Monitoring remains artifact-only and observe-only. It does not read or mutate live trading state.
- Required output flags remain covered by tests: `research_only: true`, `observe_only: true`, and `promotion_ready: false`.
- Missing required artifact files fail clearly with a `FileNotFoundError` message containing `HMM/KNN monitoring missing required artifact files`.
- The requested operator UI plus monitoring report command passed with `22 passed in 8.43s`.
