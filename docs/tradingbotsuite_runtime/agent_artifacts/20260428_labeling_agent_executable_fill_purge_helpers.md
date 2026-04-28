# Agent name

Labeling Agent

# Task received

Implement more concrete executable-entry and purge/embargo helpers for research labels.

Requested scope:

- Work in `src/tradingbotsuite/research/dataset.py` or a small new research module if cleaner.
- Add focused tests in `tests/tradingbotsuite/test_research.py` or a new focused test file.
- Create this handoff artifact.
- Do not rewire the full dataset builder if broad.
- Keep all behavior research-only and deterministic; no Hyperliquid calls.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `src/tradingbotsuite/research/dataset.py`
- `tests/tradingbotsuite/test_research.py`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_labeling_agent_executable_entry_purge_contract.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_labeling_agent_cost_exit_accounting_hardening.md`
- `src/tradingbotsuite/research/hmm_knn.py` via targeted `rg`
- `src/tradingbotsuite/core/models.py` via targeted `rg` and file head read

# Files changed

- `src/tradingbotsuite/research/dataset.py`
- `tests/tradingbotsuite/test_research.py`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_labeling_agent_executable_fill_purge_helpers.md`

# Commands/tests run

```powershell
Get-Content -Raw docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md
Get-Content -Raw src/tradingbotsuite/research/dataset.py
Get-Content -Raw tests/tradingbotsuite/test_research.py
git status --short
Get-ChildItem docs/tradingbotsuite_runtime/agent_artifacts | Select-Object -ExpandProperty Name
rg "purge|embargo|entry_price_source|simulate" src/tradingbotsuite/research tests/tradingbotsuite/test_research.py
Get-Content -Raw docs/tradingbotsuite_runtime/agent_artifacts/20260428_labeling_agent_executable_entry_purge_contract.md
Get-Content -Raw docs/tradingbotsuite_runtime/agent_artifacts/20260428_labeling_agent_cost_exit_accounting_hardening.md
rg "label_intervals_overlap|label_interval|purge" -n src/tradingbotsuite/research/hmm_knn.py
rg "class SignalDirection" -n src/tradingbotsuite/core/models.py
Get-Content -TotalCount 60 src/tradingbotsuite/core/models.py
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py -q
git diff -- src/tradingbotsuite/research/dataset.py tests/tradingbotsuite/test_research.py
git status --short
```

Focused test result:

```text
17 passed in 3.64s
```

# Decisions made

- Added `ExecutableEntrySimulation` and `simulate_executable_entry_fill()` as pure deterministic research helpers in `dataset.py`.
- The simulator uses `next_bar_open` plus directional configured slippage as the fill price proxy.
- The simulated fill time is `max(signal_bar_close_time_ms + decision_latency_ms + order_placement_latency_ms, next_bar_open_time_ms)`.
- Missing or invalid price, time, latency, cost, or direction metadata returns `promotable=False`, no fill price/time, and `reason="simulated_fill_metadata_incomplete"`.
- Complete simulated fill metadata includes latency and slippage fields recognized by `classify_label_entry_source()`, so simulated fills are promotable only when the executable metadata is complete.
- Added `purged_train_indices_for_label_intervals()` as a pure helper returning train interval positions that overlap any test label interval under optional `embargo_ms`.
- Kept existing `label_intervals_overlap()` semantics and did not rewire `ResearchDatasetBuilder` or walk-forward code in this pass.

# Assumptions

- The helper is a research-label approximation, not a venue execution model.
- `next_bar_open` is the simple executable price proxy for this pass; it is still not Hyperliquid evidence.
- Returned purge indices are zero-based positions in the supplied `train_label_intervals` sequence.
- Millisecond embargo is applied through the existing interval-overlap helper.

# Open issues or blockers

No blocker was hit and no new issue was appended.

# Handoff notes for other agents

- Backtest and evaluation work can call `purged_train_indices_for_label_intervals()` when label interval columns are available instead of using fixed bar counts.
- Data and labeling regeneration work can use `simulate_executable_entry_fill()` to produce deterministic simulated fill metadata, but real promotion still requires future venue-basis and execution evidence.
- `src/tradingbotsuite/research/archive_sources.py` had pre-existing unrelated local modifications during this pass; it was not edited.
