# Agent name

Monitoring Agent

# Task received

Add observe-only data-quality reporting for archive, market-data, and journal manifests. Keep the work pure/research-only, avoid live safe mode or operator controls, and document public report fields.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `src/tradingbotsuite/research/market_data.py`
- `src/tradingbotsuite/research/archive_sources.py`
- `src/tradingbotsuite/research/hmm_knn_monitoring.py`
- `tests/tradingbotsuite/test_archive_sources.py`
- `tests/tradingbotsuite/test_market_data_collection.py`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_binance_chart_collection.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_feature_agent_of_archive_source_contract.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_data_foundation_boundary_review.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_next_experiment_thresholds.md`

# Files changed

- `src/tradingbotsuite/research/data_quality.py`
- `tests/tradingbotsuite/test_data_quality.py`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_data_quality_reports.md`

# Commands/tests run

```powershell
Get-Content -Path docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md
Get-Content -Path src/tradingbotsuite/research/market_data.py
Get-Content -Path src/tradingbotsuite/research/archive_sources.py
Get-Content -Path src/tradingbotsuite/research/hmm_knn_monitoring.py
Get-Content -Path docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md
Get-ChildItem -Path docs/tradingbotsuite_runtime/agent_artifacts -Force
Get-Content -Path tests/tradingbotsuite/test_archive_sources.py
Get-Content -Path tests/tradingbotsuite/test_market_data_collection.py
Get-Content -Path docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_data_quality.py -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_data_quality.py tests/tradingbotsuite/test_archive_sources.py tests/tradingbotsuite/test_market_data_collection.py -q
```

Results:

- `tests/tradingbotsuite/test_data_quality.py`: `3 passed in 0.12s`
- Combined focused run after interface/error coverage: `26 passed in 0.55s`

# Decisions made

- Added `build_manifest_data_quality_report()` in `src/tradingbotsuite/research/data_quality.py`.
- Kept the function pure: it accepts manifest dictionaries, returns a report dictionary, and performs no file I/O, network calls, operator actions, safe-mode changes, model promotion, or execution actions.
- The report is always `research_only: true`, `observe_only: true`, and `promotion_ready: false`.
- The report aggregates `manifest_count`, `source_counts`, `family_counts`, `symbol_counts`, gap/duplicate totals, missing receive-time count, non-promotable count, source mismatch count, missing research-only count, zero-row count, timestamp drift flags, missing receive-time flags, stale receive-time flags, alerts, and per-manifest summaries.
- Archive source manifests are cross-checked with `validate_archive_source_manifest()` when archive-style keys are present. Market-data and journal manifests are handled through generic fields so the function remains useful before journal schemas are finalized.
- Alerts are aggregate observe-only diagnostics and include the required codes: `missing_receive_time`, `gaps_detected`, `duplicates_detected`, `source_mismatch`, `non_promotable_source`, `missing_research_only`, and `zero_row_manifest`. `timestamp_drift` and `stale_receive_time` are emitted when comparable timestamp fields exist and are inconsistent.
- Documented the public data-quality report fields in `HMM_MULTI_KNN_MODEL_SPEC.md`.

# Assumptions

- Market-data collector manifests without receive-time metadata are valid research artifacts but non-promotable diagnostics for point-in-time promotion purposes.
- Archive source descriptors remain diagnostic-only by default, so even valid archive manifests are counted as non-promotable unless a future contract explicitly proves promotion eligibility.
- Journal manifests are not fully standardized yet; the report accepts common fields such as `journal_source`, `journal_family`, receive-time metadata, gap/duplicate counts, and timestamp bounds.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` showed no open issues when checked. No issue was appended.

# Handoff notes for other agents

- Data and Feature agents can call `build_manifest_data_quality_report()` with generated archive, collector, or journal manifests before writing a higher-level handoff artifact.
- This report is artifact/report only. It must not be wired into live safe mode, live gates, sizing, Hyperliquid execution, automated promotion, retraining, or operator live controls.
- If journal schemas add new receive-time or drift fields, extend the helper field aliases and tests without changing the observe-only contract.
