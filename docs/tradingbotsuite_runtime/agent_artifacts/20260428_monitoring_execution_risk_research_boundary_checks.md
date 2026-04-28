# Monitoring Execution/Risk Research Boundary Checks

## Agent name

Monitoring plus Execution/Risk Agent

## Task received

Add or harden research-boundary validation around the new experiment, journal, and artifact flow.

Required boundary:

- Monitoring remains observe-only.
- Research artifacts remain research-only.
- `promotion_ready` remains false unless future gates explicitly pass.
- Research manifests cannot be mistaken for live signal, sizing, execution, runtime-control, Hyperliquid, or operator-control input.
- Prefer tests and docs over runtime rewiring.
- Do not connect HMM/KNN outputs to live execution, operator UI controls, Hyperliquid, sizing, or runtime control files.

## Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_RUNBOOK.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_EXECUTION_RISK_REVIEW.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_final_observe_only_check.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_hardened_artifact_followup.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_final_live_boundary_check.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_replay_determinism_contract.md`
- `src/tradingbotsuite/research/live_readiness.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `src/tradingbotsuite/research/hmm_knn_monitoring.py`
- `src/tradingbotsuite/research/hmm_knn_experiments.py`
- `src/tradingbotsuite/research/market_journal.py`
- `src/tradingbotsuite/research/market_data.py`
- `src/tradingbotsuite/research/execution_journal.py`
- `tests/tradingbotsuite/test_live_readiness.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `tests/tradingbotsuite/test_market_journal.py`
- `tests/tradingbotsuite/test_market_data_collection.py`
- `tests/tradingbotsuite/test_execution_journal.py`
- `tests/tradingbotsuite/test_operator_ui.py`

## Files changed

- `src/tradingbotsuite/research/live_readiness.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `src/tradingbotsuite/research/hmm_knn_monitoring.py`
- `src/tradingbotsuite/research/hmm_knn_experiments.py`
- `src/tradingbotsuite/research/market_journal.py`
- `src/tradingbotsuite/research/market_data.py`
- `src/tradingbotsuite/research/execution_journal.py`
- `tests/tradingbotsuite/test_live_readiness.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `tests/tradingbotsuite/test_market_journal.py`
- `tests/tradingbotsuite/test_market_data_collection.py`
- `tests/tradingbotsuite/test_execution_journal.py`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_execution_risk_research_boundary_checks.md`

Note: the current working tree also contains unrelated research diffs from other agents in `configs/v2_btc_hmm_multi_knn_research.json`, `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`, `src/tradingbotsuite/main.py`, market-journal files, and pre-existing GPU/parallel experiment edits in some files touched here. Those were not reverted.

## Behavior added

- Added `build_research_boundary_report(...)` to the existing research validation helper.
- Added `research_boundary_metadata()` for explicit non-live markers:
  - `intended_use: research_observe_only`
  - `live_signal_input: false`
  - `position_sizing_input: false`
  - `operator_control_input: false`
  - `live_execution_input: false`
  - `runtime_control_input: false`
- Research-boundary validation now blocks:
  - missing `research_only: true`
  - missing monitoring/experiment `observe_only: true`
  - `promotion_ready: true`
  - missing or non-research `intended_use`
  - truthy live/sizing/operator/runtime input flags
  - live output fields such as `execution_intents_path`, `orders_path`, or `position_sizing_path`
  - monitoring alerts that are not explicitly `observe_only`
  - experiment records whose metrics digest reports `promotion_ready: true`
- HMM/KNN artifact manifests, walk-forward metrics, monitoring reports, replay-updated metrics, and experiment manifests now emit explicit research-boundary metadata.
- Market journal, market-data collection/archive, and execution journal manifests now emit the same explicit non-live metadata.
- `monitor_hmm_knn_artifact(...)` validates the source artifact manifest and generated monitoring report before writing `monitoring_report.json`.
- `run_hmm_knn_experiment_matrix(...)` validates each artifact/metrics/monitoring triplet and records a per-experiment `research_boundary` summary. Cached artifacts must pass the boundary validator before reuse.

## Commands/tests run

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_live_readiness.py -q
```

Result:

```text
7 passed
```

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_live_readiness.py tests/tradingbotsuite/test_hmm_knn.py::test_hmm_knn_monitoring_report_is_research_only_and_observe_only tests/tradingbotsuite/test_hmm_knn.py::test_hmm_knn_cli_research_then_monitor_writes_expected_temp_artifacts tests/tradingbotsuite/test_hmm_knn.py::test_hmm_knn_monitoring_fails_clearly_when_required_artifact_is_missing tests/tradingbotsuite/test_hmm_knn.py::test_hmm_knn_experiment_runner_writes_manifest_summary_and_monitoring tests/tradingbotsuite/test_hmm_knn.py::test_hmm_knn_experiment_runner_reuses_complete_cached_artifact -q
```

Result:

```text
12 passed
```

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
```

Result:

```text
35 passed
```

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_market_journal.py tests/tradingbotsuite/test_execution_journal.py tests/tradingbotsuite/test_market_data_collection.py -q
```

Result:

```text
15 passed
```

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_live_readiness.py tests/tradingbotsuite/test_hmm_knn.py -q
```

Result:

```text
42 passed
```

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py::test_operator_artifacts_include_hmm_knn_monitoring_summary tests/tradingbotsuite/test_operator_ui.py::test_operator_research_page_keeps_hmm_knn_monitoring_observe_only -q
```

Result:

```text
2 passed
```

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite/research/live_readiness.py src/tradingbotsuite/research/hmm_knn.py src/tradingbotsuite/research/hmm_knn_monitoring.py src/tradingbotsuite/research/hmm_knn_experiments.py
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite/research/market_journal.py src/tradingbotsuite/research/execution_journal.py src/tradingbotsuite/research/market_data.py
```

Result:

```text
<no output>
```

```powershell
git diff -- src/tradingbotsuite/adapters/execution.py src/tradingbotsuite/core/engine.py src/tradingbotsuite/runtime.py src/tradingbotsuite/web/operator.py src/tradingbotsuite/web/templates/control.html src/tradingbotsuite/operator_commands.py src/tradingbotsuite/config.py
```

Result:

```text
<no output>
```

```powershell
git diff --check -- src/tradingbotsuite/research/live_readiness.py src/tradingbotsuite/research/hmm_knn.py src/tradingbotsuite/research/hmm_knn_monitoring.py src/tradingbotsuite/research/hmm_knn_experiments.py tests/tradingbotsuite/test_live_readiness.py tests/tradingbotsuite/test_hmm_knn.py
```

Result:

```text
No whitespace errors. Git reported existing LF-to-CRLF working-copy warnings.
```

## Boundary confirmation

- No live execution files were modified.
- No position sizing, Hyperliquid adapter, live accept/reject gate, runtime control, Control page, or operator live-control behavior was changed.
- The validation helper only inspects supplied payload dictionaries.
- HMM/KNN monitoring remains artifact-only and observe-only.
- Research manifests now state explicitly that they are not live signal, sizing, operator-control, live-execution, or runtime-control inputs.

## Unresolved risks

- Existing runtime can load older non-HMM model manifests through `ResearchConfig.artifact_manifest_path`; this task intentionally did not rewire runtime loading or live startup policy.
- Older already-generated HMM/KNN artifacts that lack the new explicit non-live flags will fail the new monitoring/experiment boundary validation and should be regenerated.
- The working tree contains unrelated research changes from other agents; this artifact only covers the research-boundary validation changes above.

## Open issues or blockers

No open issues or blockers.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reports no open issues.
