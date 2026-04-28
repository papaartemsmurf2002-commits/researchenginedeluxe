# HMM Multi-KNN Model Spec

## Config

Primary config:

```text
configs/v2_btc_hmm_multi_knn_research.json
```

Lookup and implementation context:

- `HMM_MULTI_KNN_INPUT_LOOKUP.md`
- `HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `HMM_MULTI_KNN_AGENT_ISSUES.md`

Important sections:

- `asset_scope`: Phase 1 contains only `BTCUSDT`.
- `regimes`: four regime definitions used for labeling outputs.
- `hmm`: state count, posterior threshold, entropy threshold, flip cooldown, backend, and emission features.
- `wt3d`: completed-bar WT3D feature parameters.
- `knn`: Lorentzian distance, k sweep, primary k, weighting, same-regime rule, and feature columns.
- `labels`: CUSUM/triple-barrier research shape and horizons.
- `meta_model`: XGBoost-first settings and fallback backend.
- `evaluation`: walk-forward splits, train fraction, fees, slippage, funding, and purge embargo.
- `acceptance`: research-only gates and reporting thresholds.

## Agent Artifact Communication

Agent-level handoffs are written under:

```text
docs/tradingbotsuite_runtime/agent_artifacts/
```

Every agent work artifact uses the filename pattern:

```text
YYYYMMDD_<agent_slug>_<task_slug>.md
```

These artifacts are the communication channel for task-local decisions, files read, files changed, commands/tests run, assumptions, blockers, and handoff notes. Agents must read relevant existing artifacts before starting and cite any artifact that influenced their work.

## CLI

Run research:

```powershell
$env:PYTHONPATH="src"
python -m tradingbotsuite.main research-hmm-knn --config configs/v2_btc_hmm_multi_knn_research.json
```

Run against an explicit dataset:

```powershell
$env:PYTHONPATH="src"
python -m tradingbotsuite.main research-hmm-knn --config configs/v2_btc_hmm_multi_knn_research.json --dataset data/research/v2-btc-research-1/btcusdt_dataset.parquet
```

Replay/summarize an artifact:

```powershell
$env:PYTHONPATH="src"
python -m tradingbotsuite.main replay-hmm-knn --manifest data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json
```

Create an observe-only monitoring report:

```powershell
$env:PYTHONPATH="src"
python -m tradingbotsuite.main monitor-hmm-knn --manifest data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json
```

## Artifacts

Input BTC Phase 1 dataset artifacts are produced by the research dataset builder under the BTC research plan output directory. The dataset manifest is part of the public Data/Labeling contract:

- `dataset_manifest.json`
  - `research_only: true`
  - `symbol: BTCUSDT`
  - `asset_scope: ["BTCUSDT"]`
  - `feature_version`
  - `label_version`
  - `label_outcome_fields`
  - `label_interval_fields`
  - `entry_price_source_summary`
  - `missing_feature_rates`
  - `raw_context_available_counts`
  - `exchange_context_summary`
  - `planned_split_summary`

All artifacts are written under:

```text
data/research/<plan_version>/
```

Required files:

- `regime_posteriors.parquet`
  - posterior columns `regime_p_0...`
  - `top_regime`
  - `top_regime_label`
  - `max_regime_probability`
  - `posterior_entropy`
  - `recent_regime_flip`
  - `regime_no_trade`
  - `regime_model_backend`
  - `walk_forward_split`
  - `source_row_index`
  - `hmm_fit_end_row`
- `knn_predictions.parquet`
  - `p_up_barrier`
  - `p_down_barrier`
  - `expected_net_return_after_costs`
  - `neighbor_agreement`
  - `neighbor_distance_quality`
  - `neighbor_count`
  - `neighbor_min_source_index`
  - `neighbor_max_source_index`
  - `knn_vote_margin`
  - `accepted_by_knn`
  - `knn_skip_reason`
- `meta_predictions.parquet`
  - input labels and features
  - `hmm_knn_feature_version`
  - regime outputs
  - KNN outputs
  - WT3D feature columns:
    - `wt3d_fast`
    - `wt3d_normal`
    - `wt3d_slow`
    - `wt3d_fast_normal_spread`
    - `wt3d_normal_slow_spread`
    - `wt3d_slope`
    - `wt3d_acceleration`
    - `wt3d_bars_since_cross`
    - `wt3d_reversal_intensity`
    - `wt3d_mtf_agreement`
  - `meta_probability`
  - `meta_model_backend`
  - `accepted_by_meta`
- `neighbor_diagnostics.csv`
  - selected `k`, weighting mode, primary-combination flag, same-regime flag, fallback flag, skip reason, source row references, query/neighbor regimes, neighbor ranks, distances, distance quality, weights, labels, and PnL multiples
- `walk_forward_metrics.json`
  - `metrics_version`
  - research-only metrics and promotion failures
  - `knn_sweep`
  - `meta_validation`
- `artifact_manifest.json`
  - config hash, feature version, dependency backends, artifact paths, and `research_only: true`
  - `feature_columns`
  - `wt3d_feature_columns`
  - `label_outcome_fields`
  - `dependencies.meta_backend`
  - `dependencies.xgboost_available`
  - `knn_settings`
  - `meta_validation`
- `monitoring_report.json`
  - `monitoring_report_version`
  - `research_only: true`
  - `observe_only: true`
  - `promotion_ready: false`
  - `artifact_identity`
  - `artifact_files`
  - `source_metrics`
  - `feature_outages`
  - `entropy_no_trade`
  - `regime_distribution_drift`
  - `neighbor_quality`
  - `funding_costs`
  - `calibration_decay`
  - `alerts`
- Archive/market-data data-quality reports built from manifest dictionaries
  - `data_quality_report_version`
  - `research_only: true`
  - `observe_only: true`
  - `promotion_ready: false`
  - `manifest_count`
  - `source_counts`
  - `family_counts`
  - `symbol_counts`
  - `gap_count_total`
  - `duplicate_count_total`
  - `missing_receive_time_count`
  - `non_promotable_count`
  - `source_mismatch_count`
  - `missing_research_only_count`
  - `zero_row_manifest_count`
  - `timestamp_drift_flags`
  - `missing_receive_time_flags`
  - `stale_receive_time_flags`
  - `alerts`
  - `manifest_summaries`

## Public Feature Columns

The artifact manifest `feature_columns` field is the public KNN feature contract. It must match the config `knn.feature_columns` and must not include label outcome fields.

Hardening and observability fields such as `label_interval_fields`, `entry_price_source_summary`, `missing_feature_rates`, `raw_context_available_counts`, `exchange_context_summary`, `regime_model_backend`, `neighbor_distance_quality`, `meta_model_backend`, and `dependencies.meta_backend` are public research artifact fields. They are diagnostics and audit inputs only; they do not authorize live gates, live sizing, Hyperliquid execution, safety behavior changes, or operator live controls.

## Research Archive Source Contract

Historical order-flow style archive sources are described by the offline contract in `src/tradingbotsuite/research/archive_sources.py`. This is not a downloader and makes no network calls.

Supported descriptor names:

- `binance_vision`
- `crypto_lake`
- `hyperliquid_archive`

Archive source manifests must include `source_name`, `source_type`, `symbol`, `data_family`, `start_time_ms`, `end_time_ms`, `row_count`, `event_time_field`, `receive_time_field` or `receive_time_unavailable_reason`, `schema_version`, `content_hash`, `normalized_fields`, and `research_only: true`.

Canonical normalized data families are `kline`, `trade`, `agg_trade`, `book_ticker`, `depth_snapshot`, `liquidation`, `funding_rate`, `open_interest`, `premium_index`, `user_fill`, `user_funding`, `order_event`, and `position_snapshot`. `order_book_l2`/`book_snapshot` are treated as `depth_snapshot` aliases, and `bbo` is treated as a `book_ticker` alias. `archive_sources.py` exposes helper contracts for each family with required, optional, and protected fields.

Point-in-time compatibility requires an event-time field. Receive-time unavailability is allowed only with an explicit reason and marks the source non-promotable. Manifest validation checks that `normalized_fields` covers each family-required field or that missing required fields are explicitly recorded in `missing_fields`, `unavailable_fields`, or `null_fields`. Unreported required normalized fields are invalid. Explicitly unavailable required fields are allowed only as diagnostic missingness and receive the `missing_required_normalized_fields` quality flag. Missing book/account execution fields must remain explicit missingness; they must not be zero-filled. Provider schema or symbol differences are represented as first-class `provider_mismatch` and `source_mismatch` quality flags. Unsupported families, missing receive time, and source-specific archive caveats are also surfaced as quality flags.

`src/tradingbotsuite/research/data_quality.py` provides a pure observe-only report builder for archive source, market-data collector, and journal manifest dictionaries. It performs no file I/O, network calls, live safe-mode changes, operator control changes, model promotion, or execution actions. Data-quality alerts are research diagnostics only and include `missing_receive_time`, `gaps_detected`, `duplicates_detected`, `source_mismatch`, `non_promotable_source`, `missing_research_only`, `zero_row_manifest`, plus timestamp and receive-time staleness alerts when comparable timestamp fields exist.

The HMM/KNN feature version emitted in artifacts is:

```text
v2-btc-hmm-knn-features-1
```

## Public Contract Freeze

These schema and version fields are public research contracts and should not change casually. Any rename, removal, semantic change, or version bump requires a coordinated docs, tests, fixture, replay, monitoring, and artifact migration review:

- Dataset manifest: `dataset_manifest_version`, `feature_version`, `label_version`, `label_outcome_fields`, `label_interval_fields`, `entry_price_source_summary`, `research_only`, `symbol`, `asset_scope`, `missing_feature_rates`, `raw_context_available_counts`, `exchange_context_summary`, and `planned_split_summary`.
- HMM/KNN artifact manifest: `artifact_manifest_version`, `feature_version`, `feature_columns`, `wt3d_feature_columns`, `label_version`, `label_horizons`, `primary_label_horizon`, `label_outcome_fields`, `knn_settings`, artifact path keys, `dependencies.hmm_backend`, `dependencies.meta_backend`, `dependencies.hmmlearn_available`, `dependencies.xgboost_available`, `meta_validation`, and `research_only`.
- Metrics and monitoring: `metrics_version`, `monitoring_report_version`, `research_only`, `observe_only`, `promotion_ready`, `promotion_failures`, `feature_outages`, `entropy_no_trade`, `regime_distribution_drift`, `neighbor_quality`, `funding_costs`, `calibration_decay`, and `alerts`.
- Archive/market-data data-quality reports: `data_quality_report_version`, `research_only`, `observe_only`, `promotion_ready`, `manifest_count`, `source_counts`, `family_counts`, `symbol_counts`, `gap_count_total`, `duplicate_count_total`, `missing_receive_time_count`, `non_promotable_count`, `source_mismatch_count`, `missing_research_only_count`, `zero_row_manifest_count`, `timestamp_drift_flags`, `missing_receive_time_flags`, `stale_receive_time_flags`, `alerts`, and `manifest_summaries`.
- Public parquet/CSV columns: `regime_posteriors.parquet`, `knn_predictions.parquet`, `meta_predictions.parquet`, and `neighbor_diagnostics.csv` fields listed above.

## Feature Construction And Scaling

WT3D construction is completed-bar only:

- `wt3d.price_column` defaults to `entry_price`.
- Non-finite prices are treated as missing.
- Missing prices are forward-filled from prior rows only; they are never backfilled from future rows.
- Initial missing prices with no prior observation are filled with `0.0`.
- WT3D uses exponentially weighted fast, normal, and slow oscillator states plus spreads, slope, clipped acceleration, bars-since-cross, reversal intensity, and shifted slow-context MTF agreement.
- Future-pivot divergence features are not part of Phase 1 public features.

KNN and HMM feature scaling is train-only:

- `robust_scaler_fit(train_frame, columns)` computes per-column medians and IQR scales only from the walk-forward train rows.
- Missing, non-finite, or non-numeric values are ignored while fitting medians and IQRs.
- All-missing or zero-IQR columns receive a neutral median of `0.0` or a scale of `1.0`.
- `RobustScalerState.transform()` maps missing transform-time values to the train median before scaling, so missing values become neutral `0.0` in robust-z space.
- Validation/test rows do not influence HMM emissions, KNN distances, or meta-model KNN feature scaling.

Current Phase 1 BTC KNN feature columns:

- `direction_long`
- `efficiency_ratio`
- `choppiness`
- `directional_slope_atr`
- `directional_di_spread`
- `range_width`
- `primary_signed_imbalance_ratio`
- `primary_sqrt_signed_imbalance_ratio`
- `top_of_book_imbalance`
- `queue_imbalance_l5`
- `spread_bps`
- `basis_bps`
- `funding_rate`
- `funding_rate_change`
- `open_interest_change_pct`
- `premium_basis_rate`
- `realized_volatility`
- `atr_percentile`
- `volatility_shock_zscore`
- `wt3d_fast`
- `wt3d_normal`
- `wt3d_slow`
- `wt3d_fast_normal_spread`
- `wt3d_normal_slow_spread`
- `wt3d_slope`
- `wt3d_acceleration`
- `wt3d_reversal_intensity`
- `wt3d_mtf_agreement`

Current HMM emission feature columns:

- `directional_slope_atr`
- `choppiness`
- `realized_volatility`
- `atr_percentile`
- `volatility_shock_zscore`
- `funding_rate`
- `open_interest_change_pct`
- `primary_signed_imbalance_ratio`
- `top_of_book_imbalance`

Public WT3D artifact columns:

- `wt3d_fast`
- `wt3d_normal`
- `wt3d_slow`
- `wt3d_fast_normal_spread`
- `wt3d_normal_slow_spread`
- `wt3d_slope`
- `wt3d_acceleration`
- `wt3d_bars_since_cross`
- `wt3d_reversal_intensity`
- `wt3d_mtf_agreement`

Label outcome fields are public research outputs, not public feature inputs:

- `gross_return`
- `fees_bps`
- `slippage_bps`
- `funding_paid_or_received`
- `time_in_trade`
- `max_adverse_excursion`
- `max_favorable_excursion`
- `barrier_hit_type`

## No-Trade Rules

A row is blocked or downgraded when:

- `max_regime_probability < 0.60`
- `posterior_entropy` exceeds the configured threshold
- the regime flipped within the cooldown window
- same-regime neighbors are unavailable
- neighbor count is below minimum
- KNN vote margin or expected value is too low
- meta probability is below threshold

## Validation Protocol

- Fit HMM, scalers, KNN pools, and meta-models on train rows only.
- Apply purge/embargo before each test window.
- Prefer `label_interval_start_ms` and `label_interval_end_ms` for purge/embargo; fixed row or bar counts are only a fallback and are not sufficient for 7-day labels.
- Treat `signal_bar_close` entry labels as non-promotable diagnostics. Executable-style entry sources require latency and cost metadata before they can be considered promotable label assumptions.
- Report pure KNN and meta-filter metrics separately.
- Include funding, fees, and slippage in expected value.
- Keep `promotion_ready` false in this phase.

## Final Validation Notes

- Repo-wide pytest uses importlib import mode through `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "--import-mode=importlib"
```

- This import-mode decision resolves duplicate test module basename collisions between `tests/test_*.py` and `tests/tradingbotsuite/test_*.py` without renaming or deleting tests.
- Final full-suite validation after the pytest configuration change passed with:

```powershell
$env:PYTHONPATH='src'
python -m pytest -q
```

Observed result from the mid-development readiness scorecard: `383 passed in 146.44s`.

- A synthetic BTC HMM/KNN artifact smoke run was created with `research-hmm-knn` in a temporary output directory. Regime, KNN, and Meta agents audited the generated `artifact_manifest.json`, parquet outputs, diagnostics, and metrics.
- A CLI/E2E fixture validation now runs `research-hmm-knn` followed by `monitor-hmm-knn` through `python -m tradingbotsuite.main`, using only synthetic BTC data and temporary output paths. It verifies expected artifact files and keeps generated artifacts outside repo data directories.
- `monitor-hmm-knn` was run against the smoke `artifact_manifest.json` and produced `monitoring_report.json` with `research_only: true`, `observe_only: true`, and `promotion_ready: false`.
- The readiness scorecard classifies the current state as research-contract validation only. No positive expectancy or live-readiness claim exists yet, and HMM/KNN outputs must not feed live gates, live sizing, Hyperliquid execution, safety behavior, or operator live controls.

## Real BTC Diagnostic Interpretation

The current real BTC artifact is a diagnostic contract run, not an acceptance pass.

- `artifact_manifest.json` reports `research_only: true`, BTC-only `asset_scope`, and `row_count: 446`.
- `walk_forward_metrics.json` reports `promotion_ready: false` with failures for negative KNN expectancy, insufficient KNN trade count, split concentration, insufficient meta trade count, missing meta long/short breakout, and research-only non-promotability.
- Pure KNN accepted `5` trades and produced costed expectancy `-1.0008811453163364`.
- Meta accepted `0` trades, so meta predictions validate schema and backend reporting only.
- `monitoring_report.json` remains `observe_only: true` and identifies high no-trade rate plus low neighbor quality.

Downstream readers must treat these fields as evidence for research triage only. They are not live signals, sizing inputs, or production acceptance outputs.
