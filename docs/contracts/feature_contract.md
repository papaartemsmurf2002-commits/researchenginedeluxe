# Feature Contract

Every feature set must have a manifest.

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
