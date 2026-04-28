# Agent name

Labeling Agent

# Task received

Create the missing labeling audit artifact. Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py tests/tradingbotsuite/test_hmm_knn.py -q
```

Audit `src/tradingbotsuite/research/dataset.py` and `src/tradingbotsuite/research/hmm_knn.py` for triple-barrier labels, fees/slippage/funding, MFE, MAE, barrier type, `label_exit_time_ms`, purge/embargo behavior, and no label leakage into features.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_btc_dataset_point_in_time_audit.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_first_hmm_knn_sweep_validation.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_meta_model_agent_audit.md`
- `src/tradingbotsuite/research/dataset.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `tests/tradingbotsuite/test_research.py`
- `tests/tradingbotsuite/test_hmm_knn.py`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_labeling_agent_triple_barrier_audit.md`

# Commands/tests run

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py tests/tradingbotsuite/test_hmm_knn.py -q
```

Exact result:

```text
..............................                                           [100%]
30 passed in 6.65s
```

Additional audit commands:

```powershell
Get-ChildItem docs\tradingbotsuite_runtime
Get-ChildItem docs\tradingbotsuite_runtime\agent_artifacts
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_data_agent_btc_dataset_point_in_time_audit.md -TotalCount 100
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_backtest_agent_first_hmm_knn_sweep_validation.md -TotalCount 100
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_meta_model_agent_audit.md -TotalCount 80
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_ISSUES.md
rg -n "LABEL_OUTCOME_COLUMNS|LabelOutcome|_label_from_future_bars|gross_return|fees_bps|slippage_bps|funding_paid_or_received|time_in_trade|max_adverse_excursion|max_favorable_excursion|barrier_hit_type|label_exit_time_ms|purge|embargo|feature_columns|label_column|pnl_column|meta_feature_columns|_leakage_safe" src\tradingbotsuite\research\dataset.py src\tradingbotsuite\research\hmm_knn.py tests\tradingbotsuite\test_hmm_knn.py tests\tradingbotsuite\test_research.py -S
```

# Audit summary

- No blocker found for the requested labeling scope.
- `HMM_MULTI_KNN_AGENT_ISSUES.md` reports no open issues.
- The labeling path remains BTC Phase 1 and research-only; no live gate, sizing, execution, Hyperliquid, safety, or operator live-control behavior is changed by these audited paths.
- The requested focused tests are green in the current environment.

# Triple-barrier label audit

`src/tradingbotsuite/research/dataset.py` keeps the primary triple-barrier semantics in `_label_from_future_bars()`:

- A `PositionState` is built with `entry_price`, `entry_time_ms`, ATR, `tp_price`, `sl_price`, and `vertical_barrier_time_ms`.
- Future bars are evaluated through `evaluate_exit_on_bar()`, preserving the live-parity order of stop loss, take profit, then vertical time barrier.
- Take-profit exits use `tp_price`, stop-loss exits use `sl_price`, and time-barrier exits use the bar close.
- Missing or insufficient future bars return `None`; the dataset builder skips those rows instead of fabricating a successful label.
- The dataset builder raises if the future label window includes the signal bar or an earlier bar.

The existing primary label contract is preserved:

- `label_exit_reason`
- `label_accept`
- `label_pnl_multiple`
- `label_version`

# Label outcome fields

`LABEL_OUTCOME_COLUMNS` defines the required public label audit fields:

- `gross_return`
- `fees_bps`
- `slippage_bps`
- `funding_paid_or_received`
- `time_in_trade`
- `max_adverse_excursion`
- `max_favorable_excursion`
- `barrier_hit_type`

`LabelOutcome` also carries `exit_price`, `exit_time_ms`, and `time_in_trade_bars`; the dataset writes these as `label_exit_price`, `label_exit_time_ms`, and `time_in_trade_bars`.

Dataset manifest coverage:

- `dataset.py` writes `label_outcome_fields` into `dataset_manifest.json`.
- `hmm_knn.py` writes `label_version`, `label_horizons`, `primary_label_horizon`, and `label_outcome_fields` into `artifact_manifest.json`.

# Fees, slippage, and funding

Dataset labels write:

- `fees_bps` from the research plan evaluation settings.
- `slippage_bps` from the research plan evaluation settings.
- `funding_paid_or_received` from point-in-time `funding_rate`, scaled by direction and actual `time_in_trade` in hours over the 8-hour funding interval.

HMM/KNN preparation preserves real dataset values when present:

- `_prepare_dataset()` only backfills `gross_return`, `fees_bps`, `slippage_bps`, and `funding_paid_or_received` when the dataset lacks those columns.
- `realized_net_return_after_costs` uses dataset `fees_bps` and `slippage_bps` when present, with funding filled to zero only if the value is missing.

HMM/KNN metrics use realized costed returns:

- `_gross_return()` prefers `gross_return`.
- `_funding_paid_or_received()` prefers `funding_paid_or_received`.
- `_realized_pnl_after_cost()` computes `gross_return - configured fee/slippage cost + funding_paid_or_received`.
- Metrics identify the basis as `realized_label_return_after_fee_slippage_funding`.

Audit note: KNN neighbor expected value still uses configured `fee_bps`, `slippage_bps`, and `_funding_cost()` for forecast EV. Realized backtest metrics use the dataset outcome fields where available.

# MFE, MAE, barrier type, and exit time

MFE/MAE handling:

- `_mfe_mae_update()` computes favorable and adverse excursion in ATR multiples.
- Long favorable excursion uses `bar.high - entry_price`; long adverse excursion uses `entry_price - bar.low`.
- Short favorable excursion uses `entry_price - bar.low`; short adverse excursion uses `bar.high - entry_price`.
- MFE/MAE are updated only while iterating through bars up to the actual exit bar. They do not use future bars after the exit condition.

Barrier and exit-time handling:

- `barrier_hit_type` is written from the actual `ExitReason`.
- `label_exit_time_ms` is written from the close time of the bar that triggered the exit.
- `time_in_trade` is the elapsed hours from signal-bar close to exit-bar close.
- `time_in_trade_bars` is the number of future bars held through the exit bar.

# Purge and embargo behavior

`hmm_knn.py` applies two protections:

- Base split embargo: `_walk_forward_frames()` starts each test window after `train_end + purge_embargo_bars`.
- Label-overlap purge: when `label_exit_time_ms` is available, `_walk_forward_frames()` moves `test_start` to the first row whose `tv_bar_time_ms` is greater than the maximum train `label_exit_time_ms` plus the configured embargo in bars.

Meta-model training KNN features are also out-of-fold:

- `_leakage_safe_meta_knn_features()` builds each train-row KNN feature from prior train rows only.
- It subtracts `purge_embargo_bars` from the candidate history end before scoring each training row.
- The source is marked as `prior_train_rows_with_embargo`.

Tests cover both behaviors:

- `test_hmm_knn_walk_forward_uses_label_exit_time_for_purge`
- `test_meta_training_knn_features_use_prior_rows_with_embargo`

# No label leakage into features

Feature construction audit:

- Dataset feature snapshots are built from historical bars, persisted decision-packet context, and point-in-time exchange context before label outcome fields are attached.
- `LABEL_OUTCOME_COLUMNS` are public artifact fields, not KNN feature inputs.
- HMM/KNN `meta_feature_columns` include KNN outputs, HMM posterior fields, and configured KNN feature columns. They do not include `label_accept`, `label_pnl_multiple`, `gross_return`, `fees_bps`, `slippage_bps`, `funding_paid_or_received`, `time_in_trade`, MFE, MAE, `barrier_hit_type`, or `label_exit_time_ms`.
- The artifact manifest records `feature_columns` separately from `label_outcome_fields`.

Tests cover this:

- `test_hmm_knn_research_writes_expected_research_only_artifacts` asserts label outcome fields are present in meta artifacts and absent from manifest `feature_columns`.
- `test_public_feature_columns_are_reflected_in_model_spec` asserts label outcome fields are documented as public outputs.

# Validation coverage observed

Focused test coverage includes:

- Deterministic research dataset build and manifest checks.
- HMM/KNN artifact generation and manifest checks.
- Label outcome preservation in `_prepare_dataset()`.
- Purge by `label_exit_time_ms`.
- Leakage-safe out-of-fold meta KNN features.
- Costed realized-return metrics.

# Final finding

The current implementation satisfies the requested Labeling Agent audit points:

- Path-dependent triple-barrier labels are used.
- Fees, slippage, and funding are explicit.
- MFE, MAE, barrier type, and `label_exit_time_ms` are emitted.
- Missing future labels are skipped rather than treated as wins.
- Purge/embargo behavior accounts for label overlap when exit times are present.
- Label outcome fields are not used as model features.
