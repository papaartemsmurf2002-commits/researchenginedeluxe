# Monitoring Agent - Experiment Performance Report

## Agent name
Monitoring Agent

## Task received
Add an experiment performance report for the current HMM/KNN research artifact. Keep the readout research-only and observe-only, and do not connect the report to live controls, execution, sizing, safe mode, retraining, or promotion.

## Files read
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_next_experiment_thresholds.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_next_experiment_matrix.md`
- `data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json`
- `data/research/v2-btc-hmm-multi-knn-1/walk_forward_metrics.json`
- `data/research/v2-btc-hmm-multi-knn-1/monitoring_report.json`

## Files changed
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_experiment_performance_report.md`

## Commands/tests run
- `rg -n "experiment performance|performance report|next_experiment|no-trade|flip rate|neighbor quality" docs/tradingbotsuite_runtime src tests`
- No pytest run was needed because this task added a documentation artifact only.

## Experiment identity
| Field | Value |
| --- | --- |
| Manifest | `data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json` |
| Dataset | `data/research/v2-btc-research-1/btcusdt_dataset.parquet` |
| Symbol | `BTCUSDT` |
| Row count | `446` |
| Plan version | `v2-btc-hmm-multi-knn-1` |
| Feature version | `v2-btc-hmm-knn-features-1` |
| Label version | `triple_barrier_live_parity_v1` |
| Primary label horizon | `24h` |
| HMM backend | `gaussian_mixture_fallback` |
| Meta backend | `random_forest_fallback` |
| Research only | `true` |
| Observe only | `true` in `monitoring_report.json` |
| Promotion ready | `false` |

## Performance summary
The current real BTC HMM/KNN artifact fails performance acceptance. The primary KNN path has too few accepted trades, negative costed expectancy, no positive split evidence, and concentrated losses. The meta path accepts zero trades. Monitoring additionally shows red no-trade, flip-rate, and neighbor-quality conditions.

| Strategy | Trades | Long | Short | Accepted rate | No-trade rate | Expectancy after cost | Profit factor | Positive split ratio | Status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Primary HMM regime Lorentzian KNN | `5` | `3` | `2` | `0.011210762331838564` | `0.9887892376681614` | `-1.0008811453163364` | `0.0` | `0.0` | Fail |
| HMM/KNN meta model | `0` | `0` | `0` | `0.0` | `1.0` | `0.0` | `null` | `0.0` | Fail |

Promotion failures reported by `walk_forward_metrics.json`:

- `knn_expectancy_after_cost_below_threshold`
- `knn_insufficient_trade_count`
- `knn_single_split_dominates_pnl`
- `meta_insufficient_trade_count`
- `meta_missing_long_short_breakout`
- `research_only_not_live_promotable`

## Split performance
| Split | Rows | KNN trades | KNN expectancy after cost | KNN no-trade rate | Meta trades | Regime no-trade rate |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `0` | `156` | `0` | `0.0` | `1.0` | `0` | `0.9423076923076923` |
| `1` | `156` | `1` | `-1.0005283261460394` | `0.9935897435897436` | `0` | `0.8717948717948718` |
| `2` | `134` | `4` | `-1.0009693501089107` | `0.9701492537313433` | `0` | `0.917910447761194` |

The primary KNN run has `max_single_split_pnl_share` of `0.8000705017118063`, so the already-negative result is also too concentrated to treat as stable evidence.

## Existing K sweep readout
The existing K sweep shows that the current primary setting is not the best diagnostic variant, but no sweep result is promotable because all costed expectancy values remain negative and evidence remains sparse.

| K | Weighting | Trades | Long | Short | Expectancy after cost | Profit factor | No-trade rate | Readout |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `16` | `inverse_distance` | `17` | `5` | `12` | `-0.5595865601001632` | `0.3210027588936527` | `0.9618834080717489` | Fail |
| `16` | `softmax` | `41` | `12` | `29` | `-0.08623056796008959` | `0.8641144044291108` | `0.9080717488789237` | Best current diagnostic trade count, still negative |
| `24` | `inverse_distance` | `7` | `4` | `3` | `-1.000869367894337` | `0.0` | `0.984304932735426` | Fail |
| `24` | `softmax` | `24` | `6` | `18` | `-0.0633558674028384` | `0.898698955231701` | `0.9461883408071748` | Best current diagnostic expectancy, still negative |
| `32` | `inverse_distance` | `5` | `3` | `2` | `-1.0008811453163364` | `0.0` | `0.9887892376681614` | Primary, fail |
| `32` | `softmax` | `18` | `5` | `13` | `-0.16751674766374525` | `0.7488859211290992` | `0.9596412556053812` | Fail |
| `48` | `inverse_distance` | `0` | `0` | `0` | `0.0` | `null` | `1.0` | No trades |
| `48` | `softmax` | `12` | `3` | `9` | `-0.7923940192309723` | `0.1361231524130713` | `0.9730941704035875` | Fail |
| `64` | `inverse_distance` | `0` | `0` | `0` | `0.0` | `null` | `1.0` | No trades |
| `64` | `softmax` | `10` | `3` | `7` | `-0.7507541541675652` | `0.16637101330584209` | `0.9775784753363229` | Fail |

The softmax variants justify further diagnostic sweeps, especially around small K, but they do not justify promotion or live use.

## Monitoring threshold scorecard
| Metric | Current value | Threshold status | Experiment requirement |
| --- | ---: | --- | --- |
| Regime no-trade rate | `0.9103139013452914` | Red | Must fall to `<= 0.60` for yellow, target `<= 0.35` |
| Recent regime flip rate | `0.8946188340807175` | Red | Must fall to `<= 0.40` for yellow, target `<= 0.20` |
| Neighbor quality mean | `0.15553586717814147` | Red | Must rise to `>= 0.25` for yellow, target `>= 0.40` |
| Neighbor quality p05 | `0.10972238899570713` | Red | Must rise to `>= 0.20` for yellow, target `>= 0.30` |
| Insufficient neighbor rate | `0.0` | Green | Must not regress above `0.05` |
| Diagnostic coverage | `1.0` | Green | Must not regress below `0.90` |
| High-outage feature count | `0` | Green | Must remain `0` for green |
| Max feature missing/non-finite rate | `0.0` | Green | Must remain `<= 0.05` for green |
| KNN Brier score | `0.24022957147733126` | Yellow | Target `<= 0.22` |
| Meta Brier score | `0.251159594803084` | Yellow | Target `<= 0.22` |
| Max regime drift | `0.1995790279372369` | Green guardrail | Must remain `<= 0.35`, target `<= 0.20` |

Active monitoring alerts:

- `high_no_trade_rate`, observe-only
- `low_neighbor_quality`, observe-only

No feature outage alert, funding alert, high entropy alert, or regime drift alert was emitted.

## Funding and cost readout
The evaluation basis includes fees, slippage, and funding:

- Fee: `5.0` bps
- Slippage: `5.0` bps
- Funding cost enabled: `true`
- PnL source: `realized_label_return_after_fee_slippage_funding`

Funding monitoring is available and did not emit a warning. The main costed-performance problem is not a missing funding field; it is negative realized label return after fees, slippage, and funding.

## Calibration readout
Calibration is available but not green:

- KNN overall Brier score: `0.24022957147733126`
- Meta overall Brier score: `0.251159594803084`
- KNN material bucket errors are around `0.08` to `0.09`
- Meta has a large material bucket around probability `0.50` with error around `0.13`

This supports diagnostic iteration only. It does not support promotion or live use.

## Decisions made
- The report grades the existing real BTC artifact as the current baseline experiment because no new experiment run was requested or produced.
- Performance status is fail because primary KNN and meta both miss trade-count, expectancy, split-stability, and promotion-readiness requirements.
- Monitoring status is mixed: feature availability and funding observability are healthy, while no-trade, flip rate, neighbor quality, and calibration remain blocking experiment-quality issues.
- The best existing diagnostic variants are `k=24 softmax` for least-negative expectancy and `k=16 softmax` for trade count, but both remain negative and non-promotable.

## Assumptions
- The current artifact directory `data/research/v2-btc-hmm-multi-knn-1` is the intended baseline for this performance report.
- Thresholds come from `20260428_monitoring_agent_next_experiment_thresholds.md`.
- The report is a documentation artifact, not a code or schema change.

## Open issues or blockers
None. `HMM_MULTI_KNN_AGENT_ISSUES.md` lists no open issues.

## Handoff notes for other agents
- Backtest should use this report as the current baseline when comparing new experiment runs.
- Regime should prioritize reducing flip-driven no-trade behavior before interpreting meta performance.
- KNN should prioritize same-regime neighbor quality and small-K/softmax diagnostics before adding complexity.
- Meta should not optimize thresholds against the current zero-final-trade path without first expanding and improving upstream KNN candidate quality.
- Execution/Risk should continue treating this artifact as research-only, observe-only, and non-promotable.
