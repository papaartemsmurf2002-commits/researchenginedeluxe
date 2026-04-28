# Agent name

Labeling Agent

# Task received

Harden the research label/data contract around executable-entry assumptions and label-window-aware purge/embargo, without rewiring live runtime.

Required scope:

- Prefer `src/tradingbotsuite/research/dataset.py` and focused tests.
- Classify label entry sources so `signal_bar_close` is non-promotable and executable-style sources require latency/cost metadata.
- Add label interval metadata for future purging.
- Add a helper or test proving fixed bar-count purge is insufficient for 7-day horizons.
- Preserve fee, slippage, funding, MFE, MAE, time-in-trade, and barrier-type label fields.
- Do not change live execution or call Hyperliquid.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_INPUT_LOOKUP.md`
- `docs/tradingbotsuite_runtime/source_inputs/tradingbotsuite_critical_audit_orchestrator_next_agent.md`
- `docs/tradingbotsuite_runtime/source_inputs/orchestrator_btc_eth_perps_architecture_review_v3.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `src/tradingbotsuite/research/dataset.py`
- `src/tradingbotsuite/core/math.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `src/tradingbotsuite/research/tradingview_import.py`
- `tests/tradingbotsuite/test_research.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- Prior Labeling/Data agent artifacts relevant to label contract and generated artifact audits.

# Files changed

- `src/tradingbotsuite/research/dataset.py`
- `tests/tradingbotsuite/test_research.py`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_labeling_agent_executable_entry_purge_contract.md`

# Commands/tests run

```powershell
git status --short --branch
Get-Content -Path docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md
Get-Content -Path docs/tradingbotsuite_runtime/HMM_MULTI_KNN_INPUT_LOOKUP.md
Get-Content -Path docs/tradingbotsuite_runtime/source_inputs/tradingbotsuite_critical_audit_orchestrator_next_agent.md
Get-Content -Path docs/tradingbotsuite_runtime/source_inputs/orchestrator_btc_eth_perps_architecture_review_v3.md
Get-Content -Path src/tradingbotsuite/research/dataset.py
Get-Content -Path src/tradingbotsuite/core/math.py
Get-Content -Path tests/tradingbotsuite/test_research.py
Get-Content -Path docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md
Get-ChildItem -Path docs/tradingbotsuite_runtime/agent_artifacts | Select-Object -ExpandProperty Name
rg -n "entry_price_source|label_interval|purge|embargo|label_outcome_fields|promot" src tests docs/tradingbotsuite_runtime -g "*.py" -g "*.md" -g "*.json"
rg -n "classify_label_entry_source|label_interval_start_ms|label_interval_end_ms|entry_price_source_promotable|label_intervals_overlap|entry_price_source_summary" src/tradingbotsuite/research/dataset.py tests/tradingbotsuite/test_research.py docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py tests/tradingbotsuite/test_hmm_knn.py -q
```

Test results:

```text
tests/tradingbotsuite/test_research.py: 15 passed in 3.51s
tests/tradingbotsuite/test_hmm_knn.py: 23 passed in 12.25s
combined command: 38 passed in 15.25s
```

# Decisions made

- Added `LabelEntrySourceMetadata` and `classify_label_entry_source()` as pure research helpers.
- `signal_bar_close` is always classified as non-promotable, even if latency/cost metadata is supplied.
- Executable-style sources, including `next_bar_open_plus_configured_slippage` and `simulated_fill`, are promotable only when at least one recognized latency field and one recognized cost field are present.
- Added dataset row fields:
  - `entry_price_source_classification`
  - `entry_price_source_promotable`
  - `entry_price_source_reason`
  - `entry_price_source_missing_required_metadata`
  - `entry_price_source_metadata_json`
  - `label_interval_start_ms`
  - `label_interval_end_ms`
- Added dataset manifest fields:
  - `label_interval_fields`
  - `entry_price_source_summary`
- Kept `LABEL_OUTCOME_COLUMNS` unchanged so existing fee/slippage/funding/MFE/MAE/time/barrier contract remains stable.
- Added `label_intervals_overlap()` as a pure helper and a test proving an 8-bar fixed embargo can still overlap a 7-day label window.
- Updated `HMM_MULTI_KNN_MODEL_SPEC.md` because new dataset manifest fields are public research contract metadata.

# Assumptions

- Current label intervals start at `signal_bar_close_time_ms` because the existing label implementation measures holding time from signal-bar close. Future executable-fill modeling can move this to a real fill timestamp without changing the field names.
- The new entry-source promotability flag is label-contract metadata only. It does not authorize live promotion and does not change runtime behavior.
- Passing plan-level fee/slippage metadata into the helper is acceptable for current dataset summary, but latency remains required before executable-style entries can become promotable.

# Open issues or blockers

No new Labeling Agent blocker was added.

`HMM_MULTI_KNN_AGENT_ISSUES.md` currently contains 1 open issue from the Execution and Risk Agent, below the 4-issue stop threshold.

# Handoff notes for other agents

- Data agents should preserve `label_interval_start_ms`, `label_interval_end_ms`, and entry-source metadata when regenerating real BTC datasets.
- Backtest agents should prefer interval-overlap purge/embargo when these fields are available. Fixed bar-count embargo remains insufficient for 7-day horizons.
- Execution/Risk agents should treat `entry_price_source_promotable` as advisory research metadata only; it is not a live promotion flag.
- Concurrent unrelated worktree changes were present while this pass finished, including data/archive source files, `src/tradingbotsuite/main.py`, and `HMM_MULTI_KNN_AGENT_ISSUES.md`. Those were not edited or reverted by this Labeling Agent pass.
