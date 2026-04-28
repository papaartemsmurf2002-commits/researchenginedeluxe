# Labeling Agent Real BTC Label Quality

Date: 2026-04-28

## Scope

Audited the available local real BTC research artifacts for label credibility:

- Dataset: `data/research/v2-btc-research-1/btcusdt_dataset.parquet`
- Dataset manifest: `data/research/v2-btc-research-1/dataset_manifest.json`
- HMM/KNN meta artifact: `data/research/v2-btc-hmm-multi-knn-1/meta_predictions.parquet`
- HMM/KNN artifact manifest: `data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json`

No live exchange data was fetched. This is an audit of the saved local artifacts only.

## Dataset Coverage

Dataset parquet:

- Rows: `1173`
- Columns: `105`
- Symbol: `BTCUSDT` only
- Direction distribution:
  - `long`: `565`
  - `short`: `608`
- Time range by `tv_bar_time_ms`:
  - `2025-12-01 13:15:00 UTC`
  - `2026-04-14 13:00:00 UTC`
- Label version: `triple_barrier_live_parity_v1`

HMM/KNN meta artifact:

- Rows: `446`
- Columns: `153`
- Symbol: `BTCUSDT` only
- Direction distribution:
  - `long`: `221`
  - `short`: `225`
- Time range by `tv_bar_time_ms`:
  - `2026-02-20 20:00:00 UTC`
  - `2026-04-14 13:00:00 UTC`

## Horizon Coverage

The HMM/KNN manifest reports research label horizon metadata:

- `label_horizons`: `["6h", "24h", "72h", "7d"]`
- `primary_label_horizon`: `24h`

The saved dataset manifest does not independently prove those horizons. Its dataset config has:

- `future_bar_limit`: `30`
- bar interval: `15m`
- maximum visible future-bar coverage from that limit: `7.5h`

This means the saved dataset artifact cannot substantiate a true primary `24h` realized label horizon, and it cannot substantiate `72h` or `7d` labels. The horizon metadata exists at the HMM/KNN artifact layer, but the real saved dataset is a stale legacy artifact relative to the current extended label contract.

## Barrier Distribution

Dataset `label_exit_reason`:

- `stop_loss`: `763`
- `take_profit`: `382`
- `time_barrier`: `28`

Dataset `label_accept`:

- `0`: `791`
- `1`: `382`
- positive rate: `0.3257`

HMM/KNN meta `barrier_hit_type`:

- `stop_loss`: `276`
- `take_profit`: `164`
- `time_barrier`: `6`

This is not an all-one-barrier artifact. The primary label classes and barrier outcomes are mixed enough for broad contract smoke checks.

## Time In Trade And Exit Time

Dataset parquet:

- `label_exit_time_ms`: absent
- `time_in_trade`: absent

HMM/KNN meta artifact:

- `label_exit_time_ms`: absent
- `time_in_trade`: present but `446 / 446` rows are null

This is a hard credibility gap for exact label accounting. The saved real BTC artifacts cannot verify actual exit timestamps, cannot validate time-to-exit distributions, and cannot prove purge/embargo based on realized label windows for this historical run.

## MFE/MAE Distribution

Dataset parquet:

- `max_adverse_excursion`: absent
- `max_favorable_excursion`: absent

HMM/KNN meta artifact:

- `max_adverse_excursion`: present but `446 / 446` rows are null
- `max_favorable_excursion`: present but `446 / 446` rows are null

This is a hard credibility gap. The available real BTC artifacts cannot validate whether MFE/MAE stop at the actual exit bar, cannot detect post-exit excursion leakage, and cannot support distribution-level reasonableness checks for excursions.

## Cost Fields

Dataset parquet:

- `gross_return`: absent
- `fees_bps`: absent
- `slippage_bps`: absent
- `funding_paid_or_received`: absent
- `realized_net_return_after_costs`: absent

HMM/KNN meta artifact:

- `gross_return`: present, `0` missing
- `fees_bps`: present, `0` missing, constant `5.0`
- `slippage_bps`: present, `0` missing, constant `5.0`
- `funding_paid_or_received`: present, `0` missing
- `realized_net_return_after_costs`: present, `0` missing

Funding by direction in the HMM/KNN meta artifact:

- long rows: constant `-0.0003`
- short rows: constant `+0.0003`

The sign convention is directionally plausible, but the values are completely uniform because the source dataset has:

- `funding_rate`: constant `0.0001` on every row
- `funding_rate_change`: constant `0.0` on every row

This is not zero funding everywhere, but it is also not strong evidence of point-in-time real funding variation.

`gross_return` in the HMM/KNN meta artifact has values near R-multiples rather than fractional returns:

- min: approximately `-0.999995`
- median: approximately `-0.999644`
- max: approximately `1.499996`

That is expected from the HMM/KNN fallback path when the dataset lacks real `gross_return`: it backfills from `label_pnl_multiple`. It is not credible as a realized fractional return field. Consequently, `realized_net_return_after_costs` mixes R-multiple-style gross values with fractional fee/slippage/funding costs in this saved artifact.

## Suspicious Patterns

Flagged:

- Dataset artifact is stale and missing all extended label outcome fields.
- HMM/KNN meta artifact is missing `label_exit_time_ms`.
- HMM/KNN meta artifact has null `time_in_trade` on every row.
- HMM/KNN meta artifact has null MFE/MAE on every row.
- `gross_return` in HMM/KNN meta appears to be a fallback copy of `label_pnl_multiple`, not a true fractional gross return.
- Funding is nonzero and directionally signed, but fully uniform because `funding_rate` is constant across all rows.
- Horizon metadata claims `24h` primary and longer research horizons, but the saved dataset manifest only shows `30` future 15m bars, or `7.5h`, and no horizon-specific realized label fields.

Not flagged:

- Labels are not all one class.
- Barriers are not all one type.
- Fees and slippage are present and nonzero in the HMM/KNN meta artifact.
- BTC-only scope is preserved in both dataset and HMM/KNN meta artifacts.

## Quality Decision

The saved real BTC artifacts are credible for coarse HMM/KNN contract execution only, not for exact label accounting.

They can demonstrate that a BTC-only local research dataset feeds HMM/KNN and produces mixed `take_profit`, `stop_loss`, and `time_barrier` outcomes. They cannot validate the hardened label contract for funding, MFE/MAE, exit time, or horizon coverage because the dataset is legacy/stale and the HMM/KNN meta artifact is relying on fallback fields.

Before any performance claim, promotion analysis, or strict label-accounting audit, the BTC dataset should be regenerated with the current dataset label contract so that the saved parquet itself contains:

- `label_exit_time_ms`
- `gross_return`
- `fees_bps`
- `slippage_bps`
- `funding_paid_or_received`
- `time_in_trade`
- `max_adverse_excursion`
- `max_favorable_excursion`
- `barrier_hit_type`

Then the HMM/KNN artifact should be regenerated from that current dataset, preserving those fields instead of backfilling them.
