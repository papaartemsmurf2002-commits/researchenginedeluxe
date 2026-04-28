# Agent name

Data Agent

# Task received

Audit BTC dataset fields, missing exchange context handling, BTC-only guard, and point-in-time safety; write a work artifact. The supervisor explicitly requested looking up `HMM_MULTI_KNN_AGENT_PROMPTS.md` before action.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_INPUT_LOOKUP.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_RUNBOOK.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_SOURCE_LOG.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_feature_agent_lookup_protocol_feature_contract.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_first_hmm_knn_sweep_validation.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_runtime_adjacent_review.md`
- `src/tradingbotsuite/research/dataset.py`
- `src/tradingbotsuite/core/features.py`
- `src/tradingbotsuite/adapters/binance.py`
- `tests/tradingbotsuite/test_research.py`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_btc_dataset_point_in_time_audit.md`

# Commands/tests run

```powershell
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_PROMPTS.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_ISSUES.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_SOURCE_LOG.md
rg -n "work artifact|artifact|Data Agent|audit|source log" docs\tradingbotsuite_runtime docs -g "*.md"
Get-ChildItem docs\tradingbotsuite_runtime\agent_artifacts -Force
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_feature_agent_lookup_protocol_feature_contract.md
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_backtest_agent_first_hmm_knn_sweep_validation.md
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_execution_risk_runtime_adjacent_review.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_INPUT_LOOKUP.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_REALIZATION_PLAN.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_MODEL_SPEC.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_RUNBOOK.md
Get-Content configs\v2_btc_hmm_multi_knn_research.json
rg -n "BTC_PHASE_1_SYMBOL|CONTEXT_MANIFEST_FIELDS|LabelOutcome|_context_manifest_summary|def build\(|signal_bar_open_time_ms|historical_feature_end_time_ms|raw_funding_rate|raw_open_interest|raw_premium|missing_feature_rates|raw_context_available_counts|exchange_context_summary|_preload_bar_history|_slice_historical_bars|_slice_future_bars" src\tradingbotsuite\research\dataset.py
rg -n "fetch_funding_context|fetch_open_interest_context|fetch_premium_context|current_payload|abs\(now_ms - as_of_ms\)|endTime" src\tradingbotsuite\adapters\binance.py
rg -n "test_research_dataset_builder_writes_parquet_and_manifest|preserves_missing_exchange_context|is_deterministic|hmm_knn_research_consumes_dataset_builder_output|signal_bar_open_time_ms|label_future_start_time_ms|context_calls|missing_funding_rate" tests\tradingbotsuite\test_research.py
$env:PYTHONPATH="src"; python -m pytest tests\tradingbotsuite\test_research.py -q
$env:PYTHONPATH="src"; python -m pytest tests\tradingbotsuite\test_hmm_knn.py -q
git status --short
```

Test results:

```text
tests\tradingbotsuite\test_research.py: 11 passed in 3.41s
tests\tradingbotsuite\test_hmm_knn.py: 18 passed in 5.38s
```

# Decisions made

- Treated this as a read-only audit plus required artifact creation. No dataset, feature, adapter, live execution, live gate, sizing, safety, Hyperliquid, or operator live-control code was changed in this task.
- Confirmed the prompt-pack protocol before action and read relevant prior artifacts. The feature artifact influenced this audit by confirming that `label_outcome_fields` are public research outputs, not KNN feature inputs. The backtest artifact influenced the validation scope. The execution-risk artifact influenced the live-behavior boundary.
- Confirmed `ResearchDatasetBuilder.build()` has an explicit Phase 1 guard: `self.plan.symbol.upper() != "BTCUSDT"` raises before data collection.
- Confirmed dataset rows include signal-bar OHLCV and audit timestamps: `signal_bar_open_time_ms`, `signal_bar_close_time_ms`, `signal_bar_open`, `signal_bar_high`, `signal_bar_low`, `signal_bar_close`, `signal_bar_volume`, `historical_feature_end_time_ms`, and future-label window fields.
- Confirmed feature rows are point-in-time: historical bars are sliced through `bisect_right(..., signal_time_ms)`, the latest feature bar must equal the TradingView signal bar, and label future bars start at `signal_time_ms + BAR_INTERVAL_MS`.
- Confirmed exchange context is requested with `as_of_ms=signal_time_ms` for funding, OI, and premium context. Binance historical endpoints use `endTime=as_of_ms` for funding, OI history, premium/mark/index klines.
- Confirmed missing exchange context remains auditable: raw fields such as `raw_funding_rate`, `raw_open_interest`, and `raw_premium_close` remain null when unavailable, while normalized model fields can be zero-filled only alongside `missing_*` flags from `numeric_feature_map()`.
- Confirmed the dataset manifest includes `research_only: true`, `asset_scope`, `missing_feature_rates`, `raw_context_available_counts`, `exchange_context_summary`, hashes, source counts, row count, and split summary.

# Available versus missing historical context fields

Audited available raw/audit fields:

- OHLCV: `signal_bar_open`, `signal_bar_high`, `signal_bar_low`, `signal_bar_close`, `signal_bar_volume`.
- Funding: `raw_funding_rate`, `raw_funding_rate_change`, `raw_time_to_next_funding_ms`, plus `funding_context_json`.
- OI: `raw_open_interest`, `raw_open_interest_change`, `raw_open_interest_change_pct`, `raw_open_interest_value`, plus `open_interest_context_json`.
- Premium/basis: `raw_premium_basis_rate`, `raw_premium_basis_abs`, `raw_premium_close`, `raw_mark_price`, `raw_index_price`, plus `premium_context_json`.
- Microstructure from captured decision packets: `raw_primary_signed_imbalance_ratio`, `raw_spread_bps`, `microstructure_context_json`, `basis_context_json`.
- TradingView/source lineage: `source`, `source_mode`, `strategy_version`, `import_batch_id`, `source_row_number`, `raw_signal_payload_json`.

Audited missingness handling:

- Funding missingness: `missing_funding_rate`, `missing_funding_rate_change`, `missing_time_to_next_funding_hours`.
- OI missingness: `missing_open_interest`, `missing_open_interest_change`, `missing_open_interest_change_pct`, `missing_open_interest_value`.
- Premium missingness: `missing_premium_basis_rate`, `missing_premium_basis_abs`, `missing_premium_close`.
- Microstructure missingness: `missing_primary_signed_imbalance_ratio`, `missing_primary_sqrt_signed_imbalance_ratio`, `missing_top_of_book_imbalance`, `missing_queue_imbalance_l1`, `missing_queue_imbalance_l5`, `missing_queue_imbalance_l10`, `missing_spread_bps`.
- Manifest missingness: `missing_feature_rates` reports dataset-level missingness rates; `exchange_context_summary` reports context source counts, per-field availability, source errors, current-source errors, and backoff rows; `raw_context_available_counts` reports non-null raw audit counts.

# Audit findings

- No blocker found for the requested scope.
- BTC-only guard is explicit and early in the dataset build path.
- Point-in-time feature alignment is enforced for bar history, signal-bar identity, exchange context `as_of_ms`, and future-label separation.
- Missing exchange context is preserved with raw nulls and `missing_*` flags; degraded endpoint metadata is preserved in context JSON and manifest summaries.
- Current-only Binance OI/premium calls are guarded to near-current rows by `abs(now_ms - as_of_ms) <= period_ms * 2`; older historical rows use historical endpoints with `endTime=as_of_ms`. This matches the Data Agent guard against using current-only fields as old historical context.
- Captured microstructure is sourced from the persisted decision packet only; no live websocket or current order-book reconstruction is used during dataset row construction.

# Assumptions

- This audit is scoped to the BTC research dataset path and its tests, not to changing feature engineering, HMM routing, KNN, meta-model, or live execution behavior.
- Near-current use of current Binance OI/premium endpoints is acceptable only as point-in-time current context for rows at the current edge, not for older historical rows.
- Existing dirty/untracked files belong to the active multi-agent HMM/KNN workstream and should not be reverted.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues before this audit, and no new issue was appended.

# Handoff notes for other agents

- Data consumers should use normalized numeric fields with their corresponding `missing_*` flags. For audits, use the `raw_*` fields and `*_context_json` fields.
- Downstream agents should not treat zero-filled normalized fields as observed values unless the matching `missing_*` flag is false.
- HMM/KNN feature consumers should keep label outcome fields out of model feature inputs; those fields are public research outputs for evaluation and backtest accounting.
- If future agents add ETH, do it as Phase 2 with a separate assignment; the current dataset builder intentionally rejects non-BTC symbols in Phase 1.
- If future agents broaden historical exchange context, preserve the existing manifest summaries so data-quality regressions remain visible.
