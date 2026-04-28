# Agent name

Feature Agent

# Task received

Make the small MD-only doc consistency fix found in the final doc audit. Add a `monitor-hmm-knn --manifest ...` example to `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`, add a one-line cross-reference in `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_SOURCE_LOG.md` pointing readers to `HMM_MULTI_KNN_INPUT_LOOKUP.md` for preserved local source filenames, and update/create this artifact. Do not change Python or tests.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_SOURCE_LOG.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_feature_agent_final_doc_consistency_check.md`

# Files changed

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_SOURCE_LOG.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_feature_agent_monitor_command_doc_fix.md`

# Commands/tests run

```powershell
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_MODEL_SPEC.md | Select-Object -First 90
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_SOURCE_LOG.md
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_feature_agent_final_doc_consistency_check.md
```

No tests were run because this task is MD-only and explicitly says not to change Python or tests.

# Decisions made

- Added the missing observe-only monitoring CLI example to the model spec:
  - `python -m tradingbotsuite.main monitor-hmm-knn --manifest data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json`
- Added a source-log cross-reference to `HMM_MULTI_KNN_INPUT_LOOKUP.md` for preserved local source filenames, including the Cyrillic DOCX name and ASCII alias.
- Did not edit Python files.
- Did not edit tests.

# Assumptions

- The model spec CLI section is the correct place for the `monitor-hmm-knn` command example.
- The source log should remain a source/dependency log, so a one-line cross-reference is preferable to duplicating local filename details.

# Open issues or blockers

None.

# Handoff notes for other agents

- The specific documentation gaps recorded in `20260428_feature_agent_final_doc_consistency_check.md` are now addressed.
- Future command additions should keep `HMM_MULTI_KNN_MODEL_SPEC.md` as the canonical command example location.
