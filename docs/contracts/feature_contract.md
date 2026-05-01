# Feature Contract

Every feature set must have a manifest.

Implementation:

- Registry: `src/tradingbotsuite/features/registry.py`
- Completed-bar alignment: `src/tradingbotsuite/features/alignment.py`
- Feature pack construction: `src/tradingbotsuite/features/packs.py`
- Train-only preprocessing: `src/tradingbotsuite/features/preprocessing.py`
- Preset manifests: `configs/features/*.json`

## Required manifest fields

```json
{
  "feature_set_id": "price_trend_wt3d_v1",
  "feature_set_version": "v1",
  "input_families": [],
  "feature_columns": [],
  "availability_columns": [],
  "point_in_time_safe": true,
  "max_feature_age_ms": null,
  "fit_scope": "train_only | stateless",
  "imputation_policy": "explicit_missingness_plus_train_only_neutral",
  "leakage_risks": [],
  "tests": []
}
```

## Rules

- Completed-bar features must use backward-only joins.
- Scalers and imputers must fit only on train rows.
- Feature missingness must be observable to models.
- Future pivots and future divergence features are forbidden unless explicitly delayed and proven non-leaking.
- WT3D is optional. Feature packs must support WT3D included, excluded, or replaced.

## Required presets

- `features_price_trend_vol`
- `features_price_trend_vol_wt3d`
- `features_perp_context_only`
- `features_price_perp_micro_no_wt`
- `features_full_context_wt3d`
- `features_full_context_no_wt`
