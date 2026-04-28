# Agent name

Feature Agent

# Task received

Fix the corrupted source filename in the lookup doc, ensure the artifact communication protocol is reflected in the prompt pack and model docs, align public feature columns with the model spec, and write a work artifact. The user explicitly requested looking up `HMM_MULTI_KNN_AGENT_PROMPTS.md` before action.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_INPUT_LOOKUP.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_RUNBOOK.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_SOURCE_LOG.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_first_hmm_knn_sweep_validation.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_runtime_adjacent_review.md`
- `src/tradingbotsuite/research/hmm_knn.py`
- `src/tradingbotsuite/research/dataset.py`
- `tests/tradingbotsuite/test_hmm_knn.py`

# Files changed

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_INPUT_LOOKUP.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `src/tradingbotsuite/research/hmm_knn.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_feature_agent_lookup_protocol_feature_contract.md`

# Commands/tests run

```powershell
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_PROMPTS.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_MODEL_SPEC.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_INPUT_LOOKUP.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_ISSUES.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_REALIZATION_PLAN.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_RUNBOOK.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_SOURCE_LOG.md
Get-Content configs\v2_btc_hmm_multi_knn_research.json
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_backtest_agent_first_hmm_knn_sweep_validation.md
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_execution_risk_runtime_adjacent_review.md
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_hmm_knn.py -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_research.py -q
```

Test results:

```text
tests\tradingbotsuite\test_hmm_knn.py: 18 passed in 4.94s
tests\tradingbotsuite\test_research.py: 11 passed in 3.09s
```

# Decisions made

- Preserved the correct UTF-8 source filename in `HMM_MULTI_KNN_INPUT_LOOKUP.md` and added an ASCII alias for tools or shells that render Cyrillic as mojibake.
- Renamed the prompt pack section from work artifact protocol to artifact communication protocol and made the handoff-channel requirement explicit.
- Added an agent artifact communication section to the model spec so model readers know where agent decisions, commands, and handoffs live.
- Added the full public feature contract to the model spec: KNN feature columns, HMM emission columns, WT3D artifact columns, and label outcome fields.
- Expanded `KNN_OUTPUT_COLUMNS` to include the public KNN prediction fields already emitted by `knn_predictions.parquet`: neighbor source bounds and skip reason.
- Added a focused test that verifies all configured public KNN/HMM/WT3D/label/KNN-output columns are reflected in `HMM_MULTI_KNN_MODEL_SPEC.md`.

# Assumptions

- The corrupted source filename problem is an encoding/rendering issue around the Cyrillic source title, so preserving the UTF-8 name plus adding an ASCII alias is safer than renaming the source document.
- Public feature columns means the manifest `feature_columns` contract and related public artifact columns documented for downstream agents.
- Existing untracked and modified files belong to this multi-agent workstream and should not be reverted.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues before this task.

# Handoff notes for other agents

- Artifact communication is now documented in both `HMM_MULTI_KNN_AGENT_PROMPTS.md` and `HMM_MULTI_KNN_MODEL_SPEC.md`.
- The model spec now lists the public feature contract; future feature additions should update both config/code and this spec, or `test_public_feature_columns_are_reflected_in_model_spec` should fail.
- Label outcome fields remain public research outputs, not KNN feature inputs.
- No live execution, live gates, sizing, Hyperliquid behavior, safety behavior, or operator live controls were touched.
