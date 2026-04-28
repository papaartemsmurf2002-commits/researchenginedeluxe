# Agent name

Data Agent

# Task received

Objective: harden generated dataset manifest and missing-context contract.

Commands requested:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py tests/tradingbotsuite/test_hmm_knn.py -q
rg -n "missing_feature_rates|raw_context_available_counts|exchange_context_summary|raw_funding|raw_open_interest|raw_premium|missing_" src tests docs/tradingbotsuite_runtime
```

Tasks:

- Add or verify tests that raw unavailable exchange context remains null while normalized fields carry matching `missing_*` flags.
- Add or verify manifest tests for `missing_feature_rates`, `raw_context_available_counts`, and `exchange_context_summary`.
- Write this artifact.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_INPUT_LOOKUP.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_RUNBOOK.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_SOURCE_LOG.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_btc_dataset_point_in_time_audit.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_generated_artifact_contract_audit.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_generated_artifact_dataset_contract_audit.md`
- `src/tradingbotsuite/research/dataset.py`
- `tests/tradingbotsuite/test_research.py`

# Files changed

- `tests/tradingbotsuite/test_research.py`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_missing_context_manifest_hardening.md`

# Commands/tests run

```powershell
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_PROMPTS.md
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py tests/tradingbotsuite/test_hmm_knn.py -q
rg -n "missing_feature_rates|raw_context_available_counts|exchange_context_summary|raw_funding|raw_open_interest|raw_premium|missing_" src tests docs/tradingbotsuite_runtime
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_INPUT_LOOKUP.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_REALIZATION_PLAN.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_MODEL_SPEC.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_RUNBOOK.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_SOURCE_LOG.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_ISSUES.md
Get-Content configs\v2_btc_hmm_multi_knn_research.json
rg -n -C 28 "test_research_dataset_builder_writes_parquet_and_manifest|test_research_dataset_builder_preserves_missing_exchange_context|missing_feature_rates|raw_context_available_counts|exchange_context_summary" tests\tradingbotsuite\test_research.py
rg -n -C 20 "raw_context_available_counts|exchange_context_summary|missing_feature_rates|raw_funding_rate|raw_open_interest|raw_premium|missing_" src\tradingbotsuite\research\dataset.py
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py tests/tradingbotsuite/test_hmm_knn.py -q
rg -n "missing_feature_rates|raw_context_available_counts|exchange_context_summary|raw_funding|raw_open_interest|raw_premium|missing_" src tests docs/tradingbotsuite_runtime
```

Validation result after hardening:

```text
34 passed in 8.38s
```

# Decisions made

- Kept implementation code unchanged because `ResearchDatasetBuilder` already writes raw audit fields, normalized numeric fields, `missing_feature_rates`, `raw_context_available_counts`, and `exchange_context_summary`.
- Hardened the existing generated-builder tests instead of adding a parallel fixture. The existing tests already build real temporary Parquet and manifest outputs, so additional assertions there directly protect the artifact contract.
- Extended the available-context manifest test to assert:
  - observed funding, OI, and premium missing rates are `0.0`;
  - premium context source counts are recorded;
  - raw OI and raw premium availability counts are recorded alongside funding.
- Extended the unavailable-context test to assert:
  - unavailable raw funding, OI, and premium fields remain null;
  - normalized funding, OI, and premium fields are zero only with matching `missing_*` flags set to `1.0`;
  - manifest `missing_feature_rates` reports the unavailable fields as `1.0`;
  - manifest `raw_context_available_counts` reports unavailable raw fields as `0`;
  - manifest `exchange_context_summary.field_available_counts` reports unavailable funding, OI, and premium fields as `0`;
  - source error and backoff summaries remain preserved.

# Assumptions

- The requested "generated dataset manifest" hardening refers to tests that build generated temporary dataset artifacts via `ResearchDatasetBuilder`, not to mutating stale checked-in data under `data/research/`.
- Existing dirty or untracked work outside this task belongs to the active multi-agent workstream and was not reverted.
- Phase 1 remains BTC-only and research-only; no live execution, gate, sizing, Hyperliquid, safety, or operator live-control behavior was touched.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues before this task. No new issue was appended.

# Handoff notes for other agents

- Downstream consumers should continue using normalized numeric exchange fields only with their paired `missing_*` flags.
- Audit workflows should prefer `raw_*` fields and context JSON/manifest summaries when determining whether historical exchange context was genuinely observed.
- If future agents add new raw exchange context columns, update both `raw_context_available_counts` expectations and the matching `missing_feature_rates` assertions in `tests/tradingbotsuite/test_research.py`.
