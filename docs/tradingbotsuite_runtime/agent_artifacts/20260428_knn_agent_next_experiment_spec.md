# Agent name

KNN Agent

# Task received

Objective: diagnose low neighbor quality and sparse accepted trades.

Requested tasks:

- Review `20260428_knn_agent_architecture_gap_review.md`.
- Propose concrete KNN experiments:
  - reduced feature subsets
  - per-regime minimum pool sizing
  - K sweep expansion or contraction
  - distance-quality thresholds
  - compatible-regime fallback as isolated experiment only
- Define exact config changes and expected metrics for each.
- Write this artifact.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_INPUT_LOOKUP.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_RUNBOOK.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_SOURCE_LOG.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_architecture_gap_review.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_real_btc_neighbor_review.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `src/tradingbotsuite/research/hmm_knn.py`
- `data/research/v2-btc-hmm-multi-knn-1/knn_predictions.parquet`
- `data/research/v2-btc-hmm-multi-knn-1/neighbor_diagnostics.csv`
- `data/research/v2-btc-hmm-multi-knn-1/regime_posteriors.parquet`
- `data/research/v2-btc-hmm-multi-knn-1/meta_predictions.parquet`
- `data/research/v2-btc-hmm-multi-knn-1/walk_forward_metrics.json`
- `data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_next_experiment_spec.md`

# Commands/tests run

Prompt and issue protocol:

```powershell
Get-Content -Path docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_PROMPTS.md -TotalCount 220
Get-Content -Path docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_ISSUES.md -TotalCount 160
```

Result:

```text
HMM_MULTI_KNN_AGENT_ISSUES.md reported no open issues.
```

Requested search, completed with `feature_columns` because the user command was truncated after `feature_c`:

```powershell
rg -n "k_values|primary_k|weighting|allow_cross_regime_fallback|neighbor_distance_quality|accepted_by_knn|feature_columns|min_neighbor_count|same_regime|fallback" src tests docs\tradingbotsuite_runtime configs\v2_btc_hmm_multi_knn_research.json
```

Key result:

```text
Current configurable KNN knobs are distance, k_values, primary_k, neighbor_weighting, primary_weighting, same_regime_only, allow_cross_regime_fallback, time_decay_half_life_bars, min_neighbor_count, vote_probability_threshold, expected_value_threshold, and feature_columns.
Current code does not yet support per-regime pool-size gates, distance-quality acceptance thresholds, or compatible-regime fallback maps.
```

Real artifact diagnostic scripts:

```powershell
$env:PYTHONPATH='src'; python <script reading real BTC KNN, diagnostics, regime, meta, metrics, and manifest artifacts>
$env:PYTHONPATH='src'; python <script reconstructing walk-forward train/test regime pools from the real BTC dataset>
```

Key result:

```text
Baseline primary: k=32, inverse_distance, accepted 5 / 446, mean distance quality 0.1555, median 0.1576.
Best existing sweep by trade count and expectancy: k=16, softmax, accepted 41 / 446, expectancy_after_cost -0.0862.
All existing sweep variants remain negative after cost.
Same-regime pools exist in every split. Minimum train pool observed: split 1 bull_trend = 47 rows.
Several configured KNN features are constant or near-constant in the real artifact because missing market context is neutralized to zero.
```

No tests were run because this task is an experiment specification artifact, not an implementation change.

# Decisions made

- Treated `20260428_knn_agent_architecture_gap_review.md` as the primary architecture-gap input. Its conclusion is that same-regime mechanics work, but useful signal is weak: sparse accepted trades, low distance quality, and negative costed expectancy.
- Used `20260428_knn_agent_real_btc_neighbor_review.md` as the quantitative baseline for experiment targets.
- Proposed experiments as config-file variants first. Experiments requiring new config schema or implementation are explicitly labeled.
- Kept all proposals BTC Phase 1 research-only. None touches live gating, sizing, Hyperliquid execution, safety behavior, runtime-mode switching, or operator live controls.

# Baseline to beat

Baseline config:

```json
{
  "version": "v2-btc-hmm-multi-knn-1",
  "knn": {
    "distance": "lorentzian",
    "k_values": [16, 24, 32, 48, 64],
    "primary_k": 32,
    "neighbor_weighting": ["inverse_distance", "softmax"],
    "primary_weighting": "inverse_distance",
    "same_regime_only": true,
    "allow_cross_regime_fallback": false,
    "min_neighbor_count": 8
  }
}
```

Real BTC baseline:

```text
primary k=32 inverse_distance
prediction rows: 446
accepted trades: 5
accepted rate: 1.12%
expectancy_after_cost: -1.0009
neighbor_distance_quality mean: 0.1555
neighbor_distance_quality median: 0.1576
neighbor_distance_quality p05: 0.1097
same-regime cross rows: 0
fallback rate: 0.0
```

Existing sweep result worth exploiting:

```text
k=16 softmax
accepted trades: 41
accepted rate: 9.19%
expectancy_after_cost: -0.0862
fallback rate: 0.0
skip reasons: none
```

Feature availability warning from the real artifact:

```text
constant or fully neutralized columns:
primary_signed_imbalance_ratio
primary_sqrt_signed_imbalance_ratio
top_of_book_imbalance
queue_imbalance_l5
spread_bps
basis_bps
funding_rate
funding_rate_change
premium_basis_rate

mostly neutralized columns:
open_interest_change_pct: 68.8% zero
wt3d_reversal_intensity: 98.0% zero
```

Same-regime train pool sizes reconstructed from the real run:

```text
split 0 train pools: range_chop 226, shock_transition 116, bear_trend 274, bull_trend 87
split 1 train pools: bull_trend 47, shock_transition 172, bear_trend 328, range_chop 320
split 2 train pools: range_chop 304, bull_trend 220, shock_transition 200, bear_trend 307
```

Interpretation: the current failure is not a simple absence of same-regime neighbors. It is a feature-distance quality problem plus acceptance sparsity after costs.

# Common evaluation contract

Run every experiment against the same real BTC dataset:

```powershell
$env:PYTHONPATH='src'
python -m tradingbotsuite.main research-hmm-knn --config <experiment_config> --dataset data/research/v2-btc-research-1/btcusdt_dataset.parquet --output-dir data/research/knn_experiments/<experiment_slug>
```

Every experiment must report these metrics from `knn_predictions.parquet`, `neighbor_diagnostics.csv`, and `walk_forward_metrics.json`:

```text
accepted_by_knn count and rate
knn_sweep trade_count, accepted_rate, expectancy_after_cost, profit_factor, long_count, short_count
neighbor_distance_quality p05, median, mean, p95 by primary and by sweep combination
same-regime cross-row count
fallback_rate and fallback_used count
skip_reasons by primary and by sweep combination
split-level trade concentration
promotion_failures
```

Exploratory improvement threshold:

```text
primary trade_count >= 25
primary expectancy_after_cost > -0.0862, which beats the best existing sweep expectancy
primary neighbor_distance_quality median >= 0.18
primary neighbor_distance_quality p05 >= 0.12
long_count > 0 and short_count > 0
same-regime cross rows == 0 unless the isolated fallback experiment is running
```

Candidate threshold:

```text
primary expectancy_after_cost >= 0.0
profit_factor > 1.0
positive_split_ratio >= 0.5
max_single_split_pnl_share <= 0.6
promotion_ready still false because this remains research-only, but KNN-specific promotion failures should shrink
```

# Experiment 1: observed-core feature subset

Purpose: remove constant and mostly unavailable market-context features from Lorentzian distance so neighbor quality is not diluted by neutralized columns.

Create:

```text
configs/experiments/v2_btc_hmm_multi_knn_exp_observed_core.json
```

Exact config changes:

```json
{
  "version": "v2-btc-hmm-multi-knn-exp-observed-core-1",
  "knn": {
    "k_values": [8, 12, 16, 24, 32],
    "primary_k": 16,
    "neighbor_weighting": ["inverse_distance", "softmax"],
    "primary_weighting": "softmax",
    "same_regime_only": true,
    "allow_cross_regime_fallback": false,
    "min_neighbor_count": 8,
    "feature_columns": [
      "direction_long",
      "efficiency_ratio",
      "choppiness",
      "directional_slope_atr",
      "directional_di_spread",
      "range_width",
      "realized_volatility",
      "atr_percentile",
      "volatility_shock_zscore",
      "wt3d_fast",
      "wt3d_normal",
      "wt3d_slow",
      "wt3d_fast_normal_spread",
      "wt3d_normal_slow_spread",
      "wt3d_slope",
      "wt3d_acceleration",
      "wt3d_mtf_agreement"
    ]
  }
}
```

Expected metrics:

```text
neighbor_distance_quality median should improve from 0.1576 to at least 0.18.
neighbor_distance_quality p05 should improve from 0.1097 to at least 0.12.
primary accepted trades should increase from 5 toward 25+ because primary is moved to k=16 softmax.
expectancy_after_cost should beat -0.0862 to justify keeping the subset.
same-regime cross rows must remain 0.
fallback_rate must remain 0.0.
```

Decision rule:

```text
Keep this as the next default candidate only if it improves quality and expectancy together.
If it improves quality but expectancy remains worse than -0.0862, use it as a diagnostic baseline, not as the default.
```

# Experiment 2: price-trend-WT3D subset

Purpose: test whether KNN similarity works better when restricted to path shape, trend/chop, volatility, and WT3D state, with all perp and microstructure fields removed.

Create:

```text
configs/experiments/v2_btc_hmm_multi_knn_exp_price_wt3d.json
```

Exact config changes:

```json
{
  "version": "v2-btc-hmm-multi-knn-exp-price-wt3d-1",
  "knn": {
    "k_values": [4, 8, 12, 16, 24],
    "primary_k": 12,
    "neighbor_weighting": ["inverse_distance", "softmax"],
    "primary_weighting": "softmax",
    "same_regime_only": true,
    "allow_cross_regime_fallback": false,
    "min_neighbor_count": 8,
    "feature_columns": [
      "direction_long",
      "efficiency_ratio",
      "choppiness",
      "directional_slope_atr",
      "directional_di_spread",
      "range_width",
      "realized_volatility",
      "atr_percentile",
      "volatility_shock_zscore",
      "wt3d_fast",
      "wt3d_normal",
      "wt3d_slow",
      "wt3d_fast_normal_spread",
      "wt3d_normal_slow_spread",
      "wt3d_slope",
      "wt3d_acceleration"
    ]
  }
}
```

Expected metrics:

```text
distance quality should be the highest of the reduced-feature experiments because low-information fields are removed.
primary trade_count should be 25 to 60 if smaller K plus softmax restores acceptance density.
If accepted trades rise but expectancy worsens, the removed perp/context fields were weak in distance but still useful as filters.
If both quality and expectancy improve, this becomes the cleanest KNN-only baseline.
```

Decision rule:

```text
Promote to the next research comparison only if primary expectancy_after_cost beats k=16 softmax baseline -0.0862 and long_count plus short_count are both nonzero.
```

# Experiment 3: OI-lite observed subset

Purpose: isolate whether sparse but non-constant open-interest context helps, while still removing fully neutralized microstructure and premium/basis fields.

Create:

```text
configs/experiments/v2_btc_hmm_multi_knn_exp_oi_lite.json
```

Exact config changes:

```json
{
  "version": "v2-btc-hmm-multi-knn-exp-oi-lite-1",
  "knn": {
    "k_values": [8, 12, 16, 24, 32],
    "primary_k": 16,
    "neighbor_weighting": ["inverse_distance", "softmax"],
    "primary_weighting": "softmax",
    "same_regime_only": true,
    "allow_cross_regime_fallback": false,
    "min_neighbor_count": 8,
    "feature_columns": [
      "direction_long",
      "efficiency_ratio",
      "choppiness",
      "directional_slope_atr",
      "directional_di_spread",
      "range_width",
      "open_interest_change_pct",
      "realized_volatility",
      "atr_percentile",
      "volatility_shock_zscore",
      "wt3d_fast",
      "wt3d_normal",
      "wt3d_slow",
      "wt3d_fast_normal_spread",
      "wt3d_normal_slow_spread",
      "wt3d_slope",
      "wt3d_acceleration",
      "wt3d_mtf_agreement"
    ]
  }
}
```

Expected metrics:

```text
Compared with Experiment 1, quality may fall slightly because open_interest_change_pct is 68.8% zero.
If expectancy improves while quality falls only mildly, OI is useful as a weak context feature.
If quality and expectancy both fall, exclude OI from KNN distance until data coverage improves.
```

Decision rule:

```text
Keep OI only if expectancy_after_cost improves versus Experiment 1 or if it materially improves split stability without reducing median quality below 0.18.
```

# Experiment 4: K contraction around the only promising sweep zone

Purpose: current sweep shows smaller K with softmax is less bad than larger K. Larger K values reduce quality and often produce zero or very sparse accepted trades.

Create:

```text
configs/experiments/v2_btc_hmm_multi_knn_exp_small_k_softmax.json
```

Exact config changes:

```json
{
  "version": "v2-btc-hmm-multi-knn-exp-small-k-softmax-1",
  "knn": {
    "k_values": [4, 6, 8, 10, 12, 16, 20, 24],
    "primary_k": 16,
    "neighbor_weighting": ["softmax"],
    "primary_weighting": "softmax",
    "same_regime_only": true,
    "allow_cross_regime_fallback": false,
    "min_neighbor_count": 6
  }
}
```

Expected metrics:

```text
k=8 through k=20 should identify whether the k=16 softmax result was a local optimum or just a broad small-K effect.
Primary accepted trades should be at least 25 because baseline k=16 softmax produced 41.
Primary expectancy_after_cost should beat -0.0862, otherwise K contraction alone is not enough.
Quality median should remain above the baseline primary 0.1576 and ideally above 0.18.
```

Decision rule:

```text
If no small-K value reaches non-negative expectancy, stop tuning K alone and prioritize feature/data/regime fixes.
```

# Experiment 5: high-K negative control

Purpose: confirm that larger neighbor sets dilute signal rather than merely failing because of the primary weighting choice.

Create:

```text
configs/experiments/v2_btc_hmm_multi_knn_exp_high_k_control.json
```

Exact config changes:

```json
{
  "version": "v2-btc-hmm-multi-knn-exp-high-k-control-1",
  "knn": {
    "k_values": [32, 48, 64, 96],
    "primary_k": 48,
    "neighbor_weighting": ["inverse_distance", "softmax"],
    "primary_weighting": "softmax",
    "same_regime_only": true,
    "allow_cross_regime_fallback": false,
    "min_neighbor_count": 8
  }
}
```

Expected metrics:

```text
Expected accepted trades: 0 to 20.
Expected quality median: below the small-K experiments.
Expected expectancy: still negative.
If high-K unexpectedly improves expectancy and split stability, the issue is not neighbor dilution and the acceptance thresholds should be reviewed.
```

Decision rule:

```text
Use this as a negative control. Do not make high K the default unless it beats the small-K experiment on expectancy, trade count, and split stability.
```

# Experiment 6: distance-quality gate

Purpose: determine whether low-quality neighbor sets are actively harmful or merely weak. This requires one implementation addition because current config does not gate `accepted_by_knn` on distance quality.

Required implementation addition:

```json
{
  "knn": {
    "min_distance_quality": 0.0
  }
}
```

Code behavior:

```text
accepted_by_knn must require neighbor_distance_quality >= knn.min_distance_quality.
walk_forward_metrics.json knn_sweep should record min_distance_quality.
artifact_manifest.json knn_settings should record min_distance_quality.
```

Create:

```text
configs/experiments/v2_btc_hmm_multi_knn_exp_quality_gate_016.json
configs/experiments/v2_btc_hmm_multi_knn_exp_quality_gate_018.json
configs/experiments/v2_btc_hmm_multi_knn_exp_quality_gate_020.json
```

Exact config changes:

```json
{
  "version": "v2-btc-hmm-multi-knn-exp-quality-gate-016",
  "knn": {
    "k_values": [8, 12, 16, 20, 24],
    "primary_k": 16,
    "neighbor_weighting": ["softmax"],
    "primary_weighting": "softmax",
    "same_regime_only": true,
    "allow_cross_regime_fallback": false,
    "min_neighbor_count": 8,
    "min_distance_quality": 0.16
  }
}
```

Repeat with:

```json
{"version": "v2-btc-hmm-multi-knn-exp-quality-gate-018", "knn": {"min_distance_quality": 0.18}}
{"version": "v2-btc-hmm-multi-knn-exp-quality-gate-020", "knn": {"min_distance_quality": 0.20}}
```

Expected metrics:

```text
0.16 should retain enough candidates to test whether quality filtering improves expectancy.
0.18 is the first serious quality gate and may reduce trade count below 25.
0.20 is expected to be too strict on the current real artifact unless reduced features materially improve quality.
If quality gating improves expectancy but trade_count falls below 25, pair it with reduced features and small-K softmax before discarding.
```

Decision rule:

```text
Reject any threshold that produces fewer than 25 primary trades unless expectancy is strongly positive and the run is clearly a scout-only diagnostic.
```

# Experiment 7: per-regime pool-size gates

Purpose: separate "same-regime pool exists" from "same-regime pool is large enough to trust" and prevent thin regimes from producing overfit local analogs.

Current code status:

```text
Current implementation only has global knn.min_neighbor_count.
It does not yet support per-regime minimum train-pool sizes.
```

Required implementation addition:

```json
{
  "knn": {
    "min_regime_pool_size": 0,
    "min_regime_pool_size_by_label": {
      "range_chop": 0,
      "bull_trend": 0,
      "bear_trend": 0,
      "shock_transition": 0
    }
  }
}
```

Code behavior:

```text
Before selecting neighbors, count same-regime train candidates for the query regime.
If the count is below the configured threshold, return skip reason insufficient_regime_pool.
Diagnostics should include candidate_pool_size and required_pool_size.
Use regime labels, not raw component IDs, because component IDs can be relabeled by train statistics across splits.
```

Create:

```text
configs/experiments/v2_btc_hmm_multi_knn_exp_pool_gate_balanced.json
```

Exact config changes:

```json
{
  "version": "v2-btc-hmm-multi-knn-exp-pool-gate-balanced-1",
  "knn": {
    "k_values": [8, 12, 16, 24],
    "primary_k": 16,
    "neighbor_weighting": ["softmax"],
    "primary_weighting": "softmax",
    "same_regime_only": true,
    "allow_cross_regime_fallback": false,
    "min_neighbor_count": 8,
    "min_regime_pool_size": 96,
    "min_regime_pool_size_by_label": {
      "range_chop": 160,
      "bull_trend": 96,
      "bear_trend": 160,
      "shock_transition": 160
    }
  }
}
```

Expected metrics:

```text
Rows from split 1 bull_trend train pool of 47 should skip as insufficient_regime_pool.
Rows from split 0 bull_trend train pool of 87 should also skip under the 96 threshold.
Shock split 0 pool of 116 should skip under the 160 threshold.
Accepted trade count may fall, but distance quality for non-skipped rows should improve.
This experiment should reveal whether thin pools are causing sparse or unstable accepted trades.
```

Decision rule:

```text
If skip rate rises sharply and expectancy does not improve, pool-size gating is too defensive for the current short dataset.
If expectancy improves with fewer but higher-quality trades, keep the gate but require a longer real dataset before any promotion discussion.
```

# Experiment 8: compatible-regime fallback, isolated only

Purpose: test whether quality improves when poor same-regime pools can borrow from compatible regimes. This must be isolated because default same-regime compliance is working and should not be weakened casually.

Current code status:

```text
Current allow_cross_regime_fallback only activates when there are no same-regime candidates.
The real run always has same-regime candidates, so simply setting allow_cross_regime_fallback to true will likely do nothing.
```

Required implementation addition:

```json
{
  "knn": {
    "compatible_regime_fallback": {
      "enabled": false,
      "trigger": "quality_or_pool",
      "min_same_regime_quality": 0.16,
      "max_fallback_neighbor_fraction": 0.25,
      "map": {
        "range_chop": ["bull_trend", "bear_trend"],
        "bull_trend": ["range_chop"],
        "bear_trend": ["range_chop"],
        "shock_transition": []
      }
    }
  }
}
```

Code behavior:

```text
Keep same-regime neighbors as the default candidate pool.
Only add compatible-regime candidates when same-regime candidate_pool_size is below the pool gate or preliminary same-regime quality is below min_same_regime_quality.
Never fallback from shock_transition unless explicitly configured.
Diagnostics must record fallback_used, fallback_trigger, compatible_regime_source, same_regime_neighbor_count, fallback_neighbor_count, and preserve query_regime / neighbor_regime evidence.
walk_forward_metrics.json must report fallback_rate by k and weighting.
```

Create:

```text
configs/experiments/v2_btc_hmm_multi_knn_exp_compatible_fallback.json
```

Exact config changes:

```json
{
  "version": "v2-btc-hmm-multi-knn-exp-compatible-fallback-1",
  "knn": {
    "k_values": [8, 12, 16, 24],
    "primary_k": 16,
    "neighbor_weighting": ["softmax"],
    "primary_weighting": "softmax",
    "same_regime_only": true,
    "allow_cross_regime_fallback": true,
    "min_neighbor_count": 8,
    "compatible_regime_fallback": {
      "enabled": true,
      "trigger": "quality_or_pool",
      "min_same_regime_quality": 0.16,
      "max_fallback_neighbor_fraction": 0.25,
      "map": {
        "range_chop": ["bull_trend", "bear_trend"],
        "bull_trend": ["range_chop"],
        "bear_trend": ["range_chop"],
        "shock_transition": []
      }
    }
  }
}
```

Expected metrics:

```text
fallback_rate should be greater than 0 and less than or equal to 25% of neighbor selections.
neighbor_distance_quality median should improve versus the same feature/K config without fallback.
Cross-regime diagnostic rows are allowed only for configured compatible pairs.
shock_transition should still have fallback_rate 0.
Expectancy must improve versus the matching no-fallback small-K softmax run; otherwise fallback adds contamination without edge.
```

Decision rule:

```text
Do not make fallback the default unless it improves expectancy, distance quality, and split stability while keeping fallback_rate bounded.
If fallback is the only way to improve quality, prefer acquiring more same-regime history before changing default behavior.
```

# Suggested run order

1. Run Experiment 4 first because it is config-only and directly exploits the best existing sweep zone.
2. Run Experiment 1 and Experiment 2 next to test whether low quality is mainly feature dilution.
3. Run Experiment 3 only if Experiment 1 is promising and OI usefulness remains unclear.
4. Implement and run Experiment 6 if quality improves but accepted trades remain noisy.
5. Implement and run Experiment 7 if thin regime pools still look unstable after reduced features.
6. Run Experiment 8 last, isolated from all same-regime default work.
7. Run Experiment 5 as a negative control when comparing final candidates.

# Assumptions

- The current real BTC artifact remains the baseline for this experiment spec.
- Reduced feature subsets are allowed because they only alter research config and artifact outputs.
- Per-regime pool-size gates, distance-quality acceptance gates, and compatible-regime fallback maps require implementation work before their configs can run.
- Regime labels are safer than raw regime IDs for per-regime config because raw component IDs may be relabeled across walk-forward fits.
- Missing context fields should stay explicit in dataset manifests; this spec only removes neutralized columns from KNN distance in selected experiments.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues before this task. The unsupported config knobs above are not blockers for this artifact because they are marked as required implementation additions.

# Handoff notes for other agents

- The strongest config-only next step is small-K softmax plus reduced observed features.
- The current artifact does not justify loosening same-regime behavior by default.
- Compatible-regime fallback should be tested only after a no-fallback small-K/reduced-feature run establishes a clean comparison.
- Do not spend time on larger K as a likely default unless the negative-control experiment unexpectedly beats small-K softmax.
- Any agent implementing new knobs should extend `artifact_manifest.json`, `walk_forward_metrics.json`, and `neighbor_diagnostics.csv` so every experiment remains auditable.
