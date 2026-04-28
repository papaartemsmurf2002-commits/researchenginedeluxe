# Monitoring Agent - Next Experiment Thresholds

## Agent name
Monitoring Agent

## Task received
Convert the current HMM/KNN monitoring alerts into experiment-monitoring requirements. Review the architecture gap artifact, define which alert metrics must improve in the next experiment, define red/yellow/green thresholds, and write this work artifact.

## Files read
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_architecture_gap_review.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_real_btc_monitoring_review.md`
- `data/research/v2-btc-hmm-multi-knn-1/monitoring_report.json`

## Files changed
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_next_experiment_thresholds.md`

## Commands/tests run
- `rg -n "high_no_trade_rate|low_neighbor_quality|feature_outage|calibration_decay|regime_distribution_drift|entropy_no_trade"`

## Current monitoring baseline
The current real BTC monitoring report remains research-only and observe-only:

- `research_only`: `true`
- `observe_only`: `true`
- `promotion_ready`: `false`
- Active observe-only alerts: `high_no_trade_rate`, `low_neighbor_quality`
- No active `feature_outage`, `regime_distribution_drift`, high entropy, funding, or calibration alert was emitted.

Current metric baselines:

| Metric | Current value | Current status |
| --- | ---: | --- |
| Regime no-trade rate | `0.9103139013452914` | Red |
| Recent regime flip rate | `0.8946188340807175` | Red |
| Neighbor quality mean | `0.15553586717814147` | Red |
| Neighbor quality p05 | `0.10972238899570713` | Red |
| Insufficient neighbor rate | `0.0` | Green |
| Same-regime diagnostic coverage | `1.0` | Green |
| High-outage feature count | `0` | Green |
| Max feature missing/non-finite rate | `0.0` | Green |
| KNN Brier score | `0.24022957147733126` | Yellow |
| Meta Brier score | `0.251159594803084` | Yellow |
| Max regime distribution drift | `0.1995790279372369` | Green guardrail |

## Next experiment requirements
The next experiment must improve the red alert areas without weakening the green controls. These are experiment-monitoring requirements only. They must not be wired into live gates, sizing, execution, safe mode, retraining, or operator live controls.

Required improvements:

| Metric | Requirement for next experiment |
| --- | --- |
| No-trade rate | Must move from red to at least yellow. Target green. |
| Flip rate | Must move from red to at least yellow. Target green. |
| Neighbor quality | Must move from red to at least yellow on both p05 and mean quality. Target green. |
| Feature outages | Must remain green. Any regression to yellow or red blocks experiment acceptance. |
| Calibration buckets | Must remain populated and improve from yellow toward green on material buckets. |

## Red/yellow/green thresholds

### No-trade rate
Metric source: `entropy_no_trade.regime_no_trade_rate`.

| Status | Threshold |
| --- | --- |
| Green | `<= 0.35` |
| Yellow | `> 0.35` and `<= 0.60` |
| Red | `> 0.60` |

The current value, `0.9103139013452914`, is red. The next experiment must reduce this to `<= 0.60`, with a target of `<= 0.35`.

### Flip rate
Metric source: `entropy_no_trade.recent_regime_flip_rate`.

| Status | Threshold |
| --- | --- |
| Green | `<= 0.20` |
| Yellow | `> 0.20` and `<= 0.40` |
| Red | `> 0.40` |

The current value, `0.8946188340807175`, is red. The next experiment must reduce this to `<= 0.40`, with a target of `<= 0.20`.

### Neighbor quality
Metric sources: `neighbor_quality.mean_neighbor_distance_quality`, `neighbor_quality.p05_neighbor_distance_quality`, `neighbor_quality.insufficient_neighbor_rate`, and `neighbor_quality.same_regime_diagnostic_coverage`.

| Status | Threshold |
| --- | --- |
| Green | `p05 >= 0.30`, `mean >= 0.40`, `insufficient_neighbor_rate == 0.0`, and `coverage >= 0.95` |
| Yellow | `p05 >= 0.20`, `mean >= 0.25`, `insufficient_neighbor_rate <= 0.05`, and `coverage >= 0.90` |
| Red | `p05 < 0.20`, `mean < 0.25`, `insufficient_neighbor_rate > 0.05`, or `coverage < 0.90` |

The current quality mean, `0.15553586717814147`, and p05, `0.10972238899570713`, are red. The next experiment must raise both to at least yellow while preserving the current green insufficient-neighbor and coverage values.

### Feature outages
Metric sources: `feature_outages.high_outage_feature_count`, per-feature `missing_rate`, and per-feature `non_finite_rate`.

| Status | Threshold |
| --- | --- |
| Green | Required feature columns present, `high_outage_feature_count == 0`, and max missing/non-finite rate `<= 0.05` |
| Yellow | Required feature columns present, `high_outage_feature_count <= 2`, and max missing/non-finite rate `<= 0.20` |
| Red | Any required feature column missing, `high_outage_feature_count > 2`, or max missing/non-finite rate `> 0.20` |

The current report is green with `0` high-outage features and `0.0` max missing/non-finite rate. The next experiment must not regress.

### Calibration buckets
Metric source: `calibration_decay` for `knn_probability` and `meta_probability`.

Bucket error is defined as:

```text
abs(mean_probability - actual_rate)
```

Material buckets are buckets with at least `25` rows.

| Status | Threshold |
| --- | --- |
| Green | Overall Brier score `<= 0.22`, every material bucket error `<= 0.08`, and at least `3` populated buckets with `>= 25` rows |
| Yellow | Overall Brier score `> 0.22` and `<= 0.26`, or any material bucket error `> 0.08` and `<= 0.15`, with at least `2` populated buckets with `>= 25` rows |
| Red | Overall Brier score `> 0.26`, any material bucket error `> 0.15`, fewer than `2` material buckets, or no calibration labels available |

The current KNN and meta calibration summaries are yellow:

- KNN Brier score: `0.24022957147733126`
- Meta Brier score: `0.251159594803084`
- KNN material bucket errors are roughly `0.08` to `0.09`
- Meta has a large material bucket around probability `0.50` with error around `0.13`

The next experiment should reduce both Brier scores to `<= 0.22` and reduce material bucket errors to `<= 0.08`. If this is not reached, the experiment must at minimum show directional improvement without losing material bucket coverage.

## Secondary guardrail: regime drift
The user-requested command includes `regime_distribution_drift`, and the architecture gap review notes drift is currently below the alert threshold. It is not one of the required-improvement metrics for the next experiment, but it should remain a guardrail.

| Status | Threshold |
| --- | --- |
| Green | Max drift `<= 0.20` |
| Yellow | Max drift `> 0.20` and `<= 0.35` |
| Red | Max drift `> 0.35` |

The current value, `0.1995790279372369`, is just inside green. A move above `0.35` should be treated as a red experiment-monitoring failure, but still observe-only.

## Decisions made
- No-trade rate, flip rate, and neighbor quality are the primary red metrics that must improve in the next experiment.
- Feature outage monitoring is already green and should be treated as a non-regression requirement.
- Calibration is not currently alerting, but bucket reliability is not strong enough for promotion; it should become an explicit yellow-to-green experiment requirement.
- Regime drift remains a secondary guardrail because it is near the green/yellow boundary but was not part of the required-improvement metric list.
- All thresholds are experiment-monitoring thresholds only. They do not imply live trading readiness or promotion readiness.

## Assumptions
- The next experiment uses the same monitoring report schema and BTC research artifact layout.
- Calibration bucket thresholds apply only where `label_accept` and probability columns are available.
- Sparse buckets below `25` rows are retained for visibility but do not determine material bucket pass/fail by themselves.
- The first walk-forward split remains the drift baseline unless a future artifact provides a training baseline distribution.

## Open issues or blockers
None.

## Handoff notes for other agents
- Backtest and Research should target lower no-trade and flip rates while improving same-regime neighbor distance quality.
- Data/Feature work should preserve the current zero-outage feature state.
- Meta/calibration work should focus on lowering Brier score and tightening the large probability bucket around `0.50`, especially for `meta_probability`.
- Execution/Risk should not wire these thresholds into live controls; they are observe-only experiment-monitoring requirements.
