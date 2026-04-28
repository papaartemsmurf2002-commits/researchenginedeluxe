# Agent name

Monitoring Agent

# Task received

After the artifact smoke run exists, run:

```powershell
python -m tradingbotsuite.main monitor-hmm-knn --manifest <artifact_manifest.json>
```

Then run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py tests/tradingbotsuite/test_hmm_knn.py::test_hmm_knn_monitoring_report_is_research_only_and_observe_only -q
```

Write this follow-up artifact.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_regime_agent_synthetic_artifact_run_audit.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_synthetic_artifact_run_audit.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_meta_model_agent_synthetic_artifact_run_audit.md`
- Generated smoke manifest: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1\artifact_manifest.json`
- Generated monitoring report: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1\monitoring_report.json`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_artifact_smoke_followup.md`
- Generated artifact outside the repo: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1\monitoring_report.json`

# Commands/tests run

Prompt and issue lookup:

```powershell
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_PROMPTS.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_ISSUES.md
```

Smoke artifact discovery and verification:

```powershell
Get-ChildItem -File docs\tradingbotsuite_runtime\agent_artifacts | Select-Object Name,LastWriteTime,Length
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_regime_agent_synthetic_artifact_run_audit.md
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_knn_agent_synthetic_artifact_run_audit.md
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_meta_model_agent_synthetic_artifact_run_audit.md
Test-Path -LiteralPath 'C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1\artifact_manifest.json'
Get-Content 'C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1\artifact_manifest.json'
```

Manifest path used:

```text
C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1\artifact_manifest.json
```

Monitor command:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main monitor-hmm-knn --manifest 'C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1\artifact_manifest.json'
```

Exact result:

```json
{
  "monitoring_report_path": "C:\\Users\\papaa\\AppData\\Local\\Temp\\hmm_knn_artifact_audit_p4o_uo8o\\research_output\\v2-btc-hmm-multi-knn-1\\monitoring_report.json"
}
```

Monitoring report summary:

```text
monitoring_report_version: v2-hmm-knn-monitoring-report-1
research_only: true
observe_only: true
promotion_ready: false
live_vs_replay_mismatch: not_available
row_count: 48
configured_feature_count: 28
high_outage_feature_count: 0
alert_count: 2
alert_codes: regime_distribution_drift, low_neighbor_quality
```

Requested pytest command:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py tests/tradingbotsuite/test_hmm_knn.py::test_hmm_knn_monitoring_report_is_research_only_and_observe_only -q
```

Exact result:

```text
......................                                                   [100%]
22 passed in 9.42s
```

# Decisions made

- Used the shared synthetic artifact smoke run from the Regime/KNN/Meta artifact-run audits instead of creating a new smoke artifact.
- Verified the smoke manifest was still present before running the monitor command.
- Ran `monitor-hmm-knn` through the CLI path with `PYTHONPATH=src` so imports resolve consistently in this repo.
- Treated the generated `monitoring_report.json` as research-only output and did not change live gates, sizing, Hyperliquid execution, safety behavior, or operator live controls.

# Assumptions

- "After the artifact smoke run exists" refers to the shared synthetic artifact run documented by Regime, KNN, and Meta agents under `C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1`.
- The requested monitor command may be run with `PYTHONPATH=src` in this local workspace to make the package importable.
- Warning alerts in the monitoring report are observe-only diagnostics, not live control state.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues.

# Handoff notes for other agents

- The smoke artifact now has a generated `monitoring_report.json`.
- The monitoring report preserves the required flags: `research_only: true`, `observe_only: true`, and `promotion_ready: false`.
- Feature outage monitoring reported `28` configured features and `0` high-outage features for the smoke artifact.
- The report emitted two observe-only warning alerts: `regime_distribution_drift` and `low_neighbor_quality`.
- The requested operator UI plus monitoring unit test command passed with `22 passed in 9.42s`.
