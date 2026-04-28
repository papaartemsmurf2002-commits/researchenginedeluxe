# Agent name

Labeling Agent

# Task received

Integrate existing executable-entry simulation more directly into research dataset labeling while preserving backward-compatible diagnostic fallback.

Scope constraints:

- Own only label executable-entry integration, focused tests, and this artifact.
- Work in `src/tradingbotsuite/research/dataset.py` and `tests/tradingbotsuite/test_research.py` if needed.
- Do not modify live execution, runtime, operator UI, Hyperliquid adapter, or broad unrelated files.

# Files read

- `src/tradingbotsuite/research/dataset.py`
- `tests/tradingbotsuite/test_research.py`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `src/tradingbotsuite/research/tradingview_import.py`
- `src/tradingbotsuite/core/math.py`
- `src/tradingbotsuite/core/models.py`

# Files changed

- `src/tradingbotsuite/research/dataset.py`
- `tests/tradingbotsuite/test_research.py`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_labeling_agent_simulated_fill_dataset_integration.md`

# Commands/tests run

```powershell
git branch --show-current
Get-Content -Raw src/tradingbotsuite/research/dataset.py
Get-Content -Raw tests/tradingbotsuite/test_research.py
Get-Content -Raw docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md
rg -n "normalized_entry_price|entry_price_source|label_interval_start_ms|next_bar_open" src/tradingbotsuite/research/dataset.py
rg -n "def evaluate_exit_on_bar|entry_time_ms" src/tradingbotsuite/core/math.py src/tradingbotsuite/core -g "*.py"
rg -n "next_bar_open|decision_latency|order_placement|slippage" src/tradingbotsuite/research/tradingview_import.py src tests -g "*.py"
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py -q
git diff -- src/tradingbotsuite/research/dataset.py tests/tradingbotsuite/test_research.py
git status --short
```

Focused test result:

```text
18 passed in 3.83s
```

# Behavior

- Added `LabelEntrySelection` and `select_label_entry_for_research()`.
- Dataset labeling now attempts `simulate_executable_entry_fill()` from raw payload fields before barrier construction.
- A simulated fill is used only when all required metadata is present and valid:
  - signal bar open/close price and time from the completed bar,
  - raw `next_bar_open` plus `next_bar_open_time_ms` or `next_bar_time_ms`,
  - raw `decision_latency_ms`,
  - raw `order_placement_latency_ms` or `order_placement_delay_ms`,
  - raw `entry_slippage_bps`, `slippage_bps`, or `configured_slippage_bps`.
- When promotable, the dataset uses:
  - `entry_price_source = "simulated_fill"`,
  - simulated fill price for `entry_price`,
  - simulated fill time for `label_interval_start_ms`,
  - executable-style classification metadata for manifest summaries.
- When simulated-fill metadata is incomplete, rows fall back to diagnostic `signal_bar_close` unless an older explicit normalized entry source is already present.
- Existing explicit normalized entry payloads remain backward-compatible; this avoids breaking chart-export rows that already include `normalized_entry_price` plus `entry_price_source`.
- Manifest `entry_price_source_summary.source_counts` and `classification_counts` now naturally distinguish `simulated_fill` executable-style rows from diagnostic `signal_bar_close` rows.

# Tests added

- Added `test_research_dataset_builder_uses_promotable_simulated_fill_metadata`.
- The test builds two labeled rows:
  - one complete simulated-fill row, proving entry source, entry price, interval start, and promotability change;
  - one incomplete simulated-fill row, proving diagnostic signal-close fallback and non-promotability.
- The test also asserts manifest summary counts split `signal_bar_close` and `simulated_fill`.

# Assumptions

- This remains a deterministic research approximation and does not imply live or venue readiness.
- Label outcome holding-time math still uses the existing triple-barrier helper; this pass only moves the public label interval start to the simulated fill time when the fill is promotable.
- Millisecond latency fields in raw payload are trusted only as supplied research metadata.

# Open issues or blockers

No blocker was hit. `HMM_MULTI_KNN_AGENT_ISSUES.md` had no open issues at the start of this pass, so no issue was appended.

# Handoff notes for other agents

- Future backtest work can rely on `label_interval_start_ms` reflecting simulated fill time for promotable simulated-fill rows.
- Execution and Risk should still treat `simulated_fill` as research-only; no live Hyperliquid execution path was touched.
- Concurrent unrelated worktree changes were present in docs and research modules outside this task; they were not modified by this Labeling Agent pass.
