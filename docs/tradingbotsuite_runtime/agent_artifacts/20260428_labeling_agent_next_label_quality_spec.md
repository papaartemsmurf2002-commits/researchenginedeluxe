# Labeling Agent Next Label Quality Spec

Date: 2026-04-28

## Scope

This artifact defines the minimum label-quality requirements for the next real BTC dataset regeneration pass.

Inputs reviewed:

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_labeling_agent_real_btc_label_distribution.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_labeling_agent_real_btc_label_quality.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_next_dataset_regeneration_spec.md`
- `src/tradingbotsuite/research/dataset.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- focused label-field search across `src`, `tests`, and `docs`

## Command Run

```powershell
rg -n "LABEL_OUTCOME_COLUMNS|barrier_hit_type|label_exit_time_ms|time_in_trade|max_adverse|max_favorable|funding_paid" src tests docs
```

Result summary:

- `src/tradingbotsuite/research/dataset.py` defines `LABEL_OUTCOME_COLUMNS` and emits extended label accounting fields.
- `src/tradingbotsuite/research/hmm_knn.py` preserves real label outcome fields when present, but backfills some fields when the source dataset is stale.
- `tests/tradingbotsuite/test_research.py` and `tests/tradingbotsuite/test_hmm_knn.py` cover funding sign, MFE/MAE stopping at the actual exit bar, artifact preservation, and `label_exit_time_ms` purge behavior.
- Prior artifacts document that current saved real BTC data is stale for exact label-quality claims.

## Prior Distribution Finding

`20260428_labeling_agent_real_btc_label_distribution.md` concluded:

- The real BTC HMM/KNN artifact is credible for coarse contract execution and costed replay diagnostics.
- The source dataset did not expose direct `barrier_hit_type`, `label_exit_time_ms`, MFE, MAE, or `funding_paid_or_received`.
- Exact label-distribution validation must be part of the next real-data regeneration pass.

The newer real BTC quality audit strengthened that finding:

- Saved dataset parquet has primary labels but lacks all extended label outcome columns.
- HMM/KNN meta output has a mixed barrier distribution, but `label_exit_time_ms` is absent and MFE/MAE/time-in-trade are null.
- Funding is nonzero and directionally signed in HMM/KNN meta output, but it is uniform because the source `funding_rate` is constant.
- Horizon metadata claims `24h` primary labels, while the saved dataset manifest only shows `30` future `15m` bars, or `7.5h`, so the saved artifact cannot substantiate a true `24h` realized label window.

## Required Dataset Label Columns

The next regenerated real BTC dataset must include these primary label columns:

- `label_accept`
- `label_pnl_multiple`
- `label_exit_reason`
- `label_version`
- `label_exit_price`
- `label_exit_time_ms`

The next regenerated dataset must also include these extended label outcome columns:

- `gross_return`
- `fees_bps`
- `slippage_bps`
- `funding_paid_or_received`
- `time_in_trade`
- `time_in_trade_bars`
- `max_adverse_excursion`
- `max_favorable_excursion`
- `barrier_hit_type`

`LABEL_OUTCOME_COLUMNS` currently covers:

- `gross_return`
- `fees_bps`
- `slippage_bps`
- `funding_paid_or_received`
- `time_in_trade`
- `max_adverse_excursion`
- `max_favorable_excursion`
- `barrier_hit_type`

`label_exit_time_ms`, `label_exit_price`, and `time_in_trade_bars` are required companion audit fields even though they are not part of `LABEL_OUTCOME_COLUMNS`.

## Cost Accounting Requirements

Fees and slippage:

- `fees_bps` must be populated on every labeled row.
- `slippage_bps` must be populated on every labeled row.
- Values must match the evaluation config used for the dataset run unless a row-level override is explicitly recorded.
- Zero fee/slippage is not acceptable unless the config explicitly sets zero and the manifest marks the run as zero-cost diagnostic.

Funding:

- `funding_paid_or_received` must be populated on every labeled row where `funding_rate` is present.
- Null funding is allowed only when point-in-time funding context is genuinely unavailable, and the matching funding missingness flag must be set.
- Funding must be direction signed:
  - long pays positive funding as a negative value
  - short receives positive funding as a positive value
  - negative funding reverses those signs
- Funding must be scaled by realized `time_in_trade`, not by a fixed horizon when actual exit timing is available.
- The manifest must report funding missingness and funding value distribution.

Gross and net returns:

- `gross_return` must be a signed fractional return from `entry_price` to `label_exit_price`.
- `gross_return` must not be a fallback copy of `label_pnl_multiple`.
- HMM/KNN outputs may include `realized_net_return_after_costs`, but it must be derived from real dataset `gross_return`, `fees_bps`, `slippage_bps`, and `funding_paid_or_received`.

## Exit Timing Requirements

`label_exit_time_ms` is mandatory for every labeled row.

Sanity rules:

- `label_exit_time_ms > signal_bar_close_time_ms`
- `label_exit_time_ms <= label_future_end_time_ms`
- `time_in_trade > 0`
- `time_in_trade_bars >= 1`
- `time_in_trade` must match elapsed time from signal-bar close to exit-bar close.
- `time_in_trade_bars` must match the number of future bars included through the actual exit bar.

Rows with insufficient future bars must be excluded or marked unlabeled. They must never be treated as wins.

## MFE/MAE Requirements

MFE/MAE fields are mandatory:

- `max_adverse_excursion`
- `max_favorable_excursion`

Sanity rules:

- Both fields must be non-null for every labeled row.
- Both fields must be numeric and non-negative.
- MFE/MAE must be computed from future bars through the actual exit bar only.
- Post-exit bars must not affect MFE/MAE.
- Long and short calculations must respect direction.
- MFE/MAE units must be documented in the manifest. Current implementation expresses them in ATR multiples.

Suspicious MFE/MAE patterns that should fail the label-quality gate:

- all MFE values are zero
- all MAE values are zero
- all rows have identical MFE or identical MAE
- negative MFE/MAE values
- values that imply impossible price movement for the available OHLC bars
- values materially above the observed high/low range implied by the exit-window bars

## Barrier Type Requirements

`barrier_hit_type` is mandatory and must match the realized exit condition.

Allowed values:

- `take_profit`
- `stop_loss`
- `time_barrier`

The dataset must preserve `label_exit_reason` for backward compatibility, but `barrier_hit_type` is the auditable label-outcome field used for distribution checks.

Minimum distribution sanity checks:

- At least two barrier types should be present in a normal real BTC regeneration run.
- If all rows have one barrier type, the run must fail label-quality review unless the manifest explains a deliberately narrow diagnostic sample.
- `label_accept == 1` should align with `take_profit` under the current triple-barrier semantics.
- `label_accept == 0` should align with `stop_loss` or `time_barrier`.
- Null `barrier_hit_type` count must be `0` for labeled rows.
- Unknown barrier values must fail the label-quality gate.

Recommended warning thresholds for a full real BTC dataset:

- warn if the dominant barrier type is above `90%`
- fail if the dominant barrier type is above `98%`
- warn if `time_barrier` is `0` and the sample spans enough volatility regimes to expect some vertical exits
- fail if `take_profit` or `stop_loss` is absent in a non-diagnostic run

## Horizon Requirements

The current HMM/KNN research config advertises:

- `6h`
- `24h`
- `72h`
- `7d`
- primary horizon: `24h`

The next real dataset must make horizon semantics explicit.

Required for the primary horizon:

- Primary label fields above must correspond to the configured primary horizon.
- The manifest must record `primary_label_horizon`.
- The future-bar coverage must be sufficient for the primary horizon. For `15m` bars, `24h` requires at least `96` future bars.

If horizon-specific labels are emitted, use names that make leakage impossible to miss, for example:

- `label_accept_6h`
- `label_pnl_multiple_6h`
- `label_exit_reason_6h`
- `label_exit_time_ms_6h`
- `barrier_hit_type_6h`
- `time_in_trade_6h`
- `max_adverse_excursion_6h`
- `max_favorable_excursion_6h`
- `gross_return_6h`
- `funding_paid_or_received_6h`

Repeat that pattern for `24h`, `72h`, and `7d` if those horizons are materialized.

If horizon-specific labels are not emitted, the manifest must state that `6h`, `72h`, and `7d` are metadata-only for that run and that the dataset rows carry only the primary `24h` label contract.

## Minimum Coverage Checks

The next regeneration pass must write a label-quality summary in the dataset manifest with:

- row count
- labeled row count
- unlabeled/skipped row count
- skip reasons for missing future bars
- `label_accept` distribution
- `barrier_hit_type` distribution
- `time_in_trade` quantiles
- `time_in_trade_bars` quantiles
- `gross_return` quantiles
- `label_pnl_multiple` quantiles
- MFE quantiles
- MAE quantiles
- `fees_bps` distribution
- `slippage_bps` distribution
- `funding_paid_or_received` quantiles
- funding missing count
- `label_exit_time_ms` missing count
- label horizon coverage in bars and hours

Minimum pass criteria:

- BTC-only scope: all rows are `BTCUSDT`.
- `label_version == triple_barrier_live_parity_v1`.
- Required label columns are present in parquet and listed in manifest.
- Required label columns are non-null on all labeled rows, except funding when point-in-time funding is unavailable and explicitly marked missing.
- At least `95%` of source signal rows should be labeled for a normal full regeneration run.
- `label_exit_time_ms` missing count must be `0` for labeled rows.
- MFE/MAE missing count must be `0` for labeled rows.
- `time_in_trade` missing count must be `0` for labeled rows.
- Barrier distribution must include at least two barrier types for a normal full run.
- The dominant barrier type must not exceed the fail threshold without an explicit diagnostic waiver.
- No label outcome columns may appear in HMM emission features, KNN feature columns, scaler inputs, or meta-filter feature inputs.

## Artifact Preservation Requirements

After dataset regeneration, HMM/KNN artifact generation must preserve real dataset label fields rather than inventing placeholders.

Required HMM/KNN manifest checks:

- `label_version` matches dataset manifest.
- `label_outcome_fields` lists all extended label outcome fields present in the meta artifact.
- `feature_columns` does not include label columns.
- `meta_feature_columns` does not include label columns.
- `primary_label_horizon` is recorded.
- `label_horizons` is recorded.

Required HMM/KNN parquet checks:

- `meta_predictions.parquet` preserves:
  - `label_exit_time_ms`
  - `barrier_hit_type`
  - `gross_return`
  - `fees_bps`
  - `slippage_bps`
  - `funding_paid_or_received`
  - `time_in_trade`
  - `time_in_trade_bars`
  - `max_adverse_excursion`
  - `max_favorable_excursion`
  - `realized_net_return_after_costs`
- `label_exit_time_ms` must be available so walk-forward purge can exclude overlapping label windows.
- MFE/MAE/time-in-trade must not be all null.

## Quality Gate Decision

A next real BTC dataset can be used for research diagnostics only if it fails any of the checks above.

It can be used for strict label-quality review only when:

- primary horizon coverage is proven
- exit timestamps are present
- time-in-trade is populated
- MFE/MAE are populated and plausible
- fee/slippage/funding are explicitly accounted
- barrier distribution is not degenerate
- label fields are excluded from feature inputs
- manifest summaries make missingness and horizon coverage auditable

No live-readiness, promotion, sizing, execution, Hyperliquid, or operator-control claim is implied by satisfying this label-quality spec.
