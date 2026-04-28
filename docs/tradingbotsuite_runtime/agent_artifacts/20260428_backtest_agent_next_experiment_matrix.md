# Backtest Agent Next Experiment Matrix

Date: 2026-04-28

## Objective

Combine the new Data, Regime, KNN, Meta, Labeling, and Monitoring experiment specs into one ranked next-experiment matrix.

## Source Artifacts Read

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_next_dataset_regeneration_spec.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_regime_agent_next_experiment_spec.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_next_experiment_spec.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_meta_model_agent_next_experiment_spec.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_labeling_agent_next_label_quality_spec.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_next_experiment_thresholds.md`

## Baseline Constraints

- Current real BTC dataset: `data/research/v2-btc-research-1/btcusdt_dataset.parquet`
- Current real BTC HMM/KNN manifest: `data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json`
- Current acceptance status: not accepted.
- Current KNN expectancy after fees/slippage/funding: `-1.0008811453163364`
- Current pure KNN accepted trades: `5`
- Current meta accepted trades: `0`
- Current regime no-trade rate: `0.9103139013452914`
- Current recent regime flip rate: `0.8946188340807175`
- Current neighbor quality mean: `0.15553586717814147`
- Current neighbor quality p05: `0.10972238899570713`
- Current KNN Brier score: `0.24022957147733126`
- Current meta Brier score: `0.251159594803084`

The current dataset is usable for diagnostics, but the Data and Labeling specs both warn that missing exchange context and incomplete label outcome fields prevent strong performance claims.

## Ranked Experiment Matrix

| Rank | Experiment name | Owning agent | Config/data change | Expected metric movement | Risk | Run order | New data required? | Can run on current artifacts? |
| ---: | --- | --- | --- | --- | --- | ---: | --- | --- |
| 1 | Regenerate BTC dataset with exchange context quality gates | Data | Regenerate BTC dataset with signed flow, top-of-book/queue imbalance, spread, OI/OI change, basis/premium, funding coverage, manifest `quality_gates`, `raw_context_available_counts`, and per-family `exchange_context_summary`. | Better KNN distance quality and more meaningful HMM emissions; lower feature-neutralization risk; current target missingness: funding `<=2%`, OI `<=20%`, basis/premium `<=10%`, spread/book/flow `<=15%`. | Requires authorized historical extraction or local cache availability; if context remains missing, output is diagnostic only. | 1 | Yes | No |
| 2 | Regenerate labels with full triple-barrier audit fields | Labeling | Add/preserve `label_exit_time_ms`, `label_exit_price`, `time_in_trade_bars`, `gross_return`, `fees_bps`, `slippage_bps`, `funding_paid_or_received`, MFE, MAE, and `barrier_hit_type`; prove 24h primary horizon requires at least 96 future 15m bars. | Makes costed expectancy, horizon stability, purge/embargo, MFE/MAE, and barrier distribution auditable; should resolve current insufficient-data horizon and label-quality gates. | May reduce usable rows if future-bar coverage is insufficient; exposes current 7.5h-vs-24h ambiguity. | 2 | Yes | No |
| 3 | Regime flip-cooldown sensitivity | Regime | Sweep `hmm.flip_cooldown_bars`: `0`, `1`, `2`, `3`, `4`, `6` on current real BTC dataset. | Should separate policy-induced no-trade from model instability; target no-trade rate moves from red `0.9103` toward `<=0.60` yellow while preserving all four regimes. | Lower cooldown may admit noisy rows and increase losing KNN candidates. | 3 | No | Yes, with research rerun on current dataset |
| 4 | KNN small-K softmax sweep | KNN | Config-only sweep with `k_values: [4,6,8,10,12,16,20,24]`, `primary_k: 16`, `primary_weighting: softmax`, `min_neighbor_count: 6`. | Exploits existing best zone: prior `k=16 softmax` had `41` trades and expectancy `-0.0862`; target primary trades `>=25`, expectancy better than `-0.0862`, quality median above `0.1576` and ideally `>=0.18`. | Could increase trade count without positive expectancy; K-only tuning may overfit the stale/incomplete dataset. | 4 | No | Yes, with research rerun on current dataset |
| 5 | KNN observed-core feature subset | KNN | Remove constant/neutralized perp and microstructure fields from KNN distance; use observed price/trend/volatility/WT3D feature set; `primary_k: 16`, softmax. | Neighbor quality median should improve from `0.1576` to `>=0.18`, p05 from `0.1097` to `>=0.12`; accepted trades should move toward `25+`. | Removing context can improve geometry while losing real market-condition filters. | 5 | No | Yes, with research rerun on current dataset |
| 6 | Regime posterior threshold sensitivity | Regime | Sweep `hmm.posterior_threshold`: `0.45`, `0.50`, `0.60`, `0.70`, `0.80`. | Confirms whether low top-regime probability drives no-trade; expected small effect because baseline low-probability rate is about `8.07%`. | Low impact if cooldown dominates; very loose threshold may admit weak regimes. | 6 | No | Yes, with research rerun on current dataset |
| 7 | Regime entropy threshold sensitivity | Regime | Sweep `hmm.entropy_threshold`: `0.45`, `0.60`, `0.78`, `0.90`, `1.01`. | Tests whether entropy can replace some cooldown strictness; monitor high-entropy rate, entropy p95, no-trade rate, and tradeable rows. | Strict entropy can reduce already sparse candidates; loose entropy may add unstable rows. | 7 | No | Yes, with research rerun on current dataset |
| 8 | KNN price-trend-WT3D subset | KNN | Config-only KNN subset using path shape, trend/chop, volatility, and WT3D; remove perp and microstructure fields; `primary_k: 12`, softmax. | Should maximize distance quality among reduced-feature tests; target `25` to `60` trades and expectancy better than `-0.0862`. | May discard useful sparse context; positive movement could be dataset-specific. | 8 | No | Yes, with research rerun on current dataset |
| 9 | Meta threshold diagnostic ladder | Meta-Model | Diagnostic thresholds `0.55`, `0.525`, `0.50`, `0.49`, `0.475`, `0.45`, `0.40`; report probability-only, KNN-intersection, and regime-allowed counts separately. | Should prove whether meta thresholding matters; expected full-formula final trades remain `0` on current artifacts because KNN candidates are regime-vetoed. | Easy to misread as performance tuning; all current KNN candidates are losing labels. | 9 | No | Yes, can compute from current artifacts or rerun diagnostic |
| 10 | Monitoring red-to-yellow acceptance overlay | Monitoring | Apply observe-only thresholds to every experiment: no-trade `<=0.60`, flip `<=0.40`, neighbor p05 `>=0.20`, neighbor mean `>=0.25`, feature outages remain green, calibration improves. | Converts experiment outputs into consistent pass/fail/yellow/green diagnostics; should prevent accepting a run that improves one metric while degrading controls. | Thresholds are not live gates; wiring them into live controls would violate scope. | 10 | No | Yes |
| 11 | XGBoost research-extra meta run | Meta-Model | Run same dataset/config in an environment where `xgboost` is importable; verify `meta_backend: xgboost`. | May improve probability separation and KNN-candidate ranking; target lower meta Brier from `0.2512` toward `<=0.22` and better bucket reliability. | Does not solve upstream sparse/vetoed KNN candidates; dependency/environment drift. | 11 | No | Yes, with research rerun on current dataset |
| 12 | KNN OI-lite observed subset | KNN | Keep sparse OI/OI-change signal while removing fully neutralized microstructure and premium/basis fields. | Tests whether OI helps distance quality after removing fully missing fields; expected quality better than baseline if OI is informative. | Current OI is highly missing/neutralized, so result may be noisy until Data regeneration. | 12 | No, but better after new data | Yes, diagnostic only |
| 13 | Pure KNN-only candidate expansion baseline | Meta-Model / KNN | Relax KNN candidate thresholds before meta: vote probability `0.55`, `0.52`, `0.50`; expected value `0.0`, `-0.05`, `-0.10`; compare regime-vetoed and regime-allowed rows separately. | Establishes whether KNN can produce at least `25` realized candidates before meta filtering; expected to reveal whether meta work is premature. | Relaxed thresholds can add losing trades; must remain diagnostic and costed. | 13 | No | Yes, with research rerun or artifact-level diagnostic |
| 14 | Regime emission feature subset ablation | Regime | Test `price-vol-core`, `trend-chop-vol-minimal`, `no-orderbook`, `no-perp`, `vol-shock-only`, and `trend-chop-only` HMM emission sets. | Target lower flip rate, longer regime run length, all four regimes preserved, range/shock each `>=5%`. | Can collapse semantic regimes or hide useful perp/orderbook state; current missing context makes some variants hard to interpret. | 14 | No, but better after new data | Yes, diagnostic only |
| 15 | Distance-quality gate | KNN | Requires implementation of `knn.min_distance_quality`; test `0.16`, `0.18`, `0.20`. | Should show whether low-quality neighbors are harmful; target better expectancy without dropping below `25` trades unless scout-only. | Requires code/config schema change; may starve already sparse candidate set. | 15 | No | Yes, after implementation |
| 16 | Meta trained after expanded KNN candidate mask | Meta-Model | Requires expanded KNN candidate mask and candidate-conditioned meta training while preserving leakage controls. | Should align meta training population to the actual decision surface; target improved post-cost expectancy without collapsing trade count or long/short coverage. | Requires implementation and enough expanded candidates; premature before KNN candidate quality improves. | 16 | No, but better after new data | Yes, after KNN expansion implementation |
| 17 | Longer training history / split sensitivity | Regime | Sweep `train_fraction`, `min_training_rows`, and `walk_forward_splits`: e.g. `0.70/50/3`, `0.80/50/3`, `0.60/200/3`, `0.70/200/2`, `0.80/300/1`. | Tests whether refit boundaries or short train windows drive regime churn; target lower flip rate without starving validation rows. | Fewer scored rows can make results look stable but less reliable. | 17 | No | Yes, with research rerun on current dataset |
| 18 | Per-regime pool-size gates | KNN | Requires implementation of `min_regime_pool_size` and per-label thresholds such as range/bear/shock `160`, bull `96`; diagnostics include candidate/required pool sizes. | Should improve quality for non-skipped rows and reveal thin-regime overfit; may reduce unstable trades. | Likely reduces trade count sharply on current short dataset. | 18 | No, but better with longer data | Yes, after implementation |
| 19 | Compatible-regime fallback, isolated | KNN | Requires implementation of bounded compatible fallback triggered by quality or pool size; max fallback neighbor fraction `0.25`; no shock fallback. | Could improve quality where same-regime pool is weak; target bounded fallback rate, improved expectancy, and split stability. | Cross-regime contamination risk; should remain isolated and last. | 19 | No, but better with longer data | Yes, after implementation |
| 20 | KNN high-K negative control | KNN | Config-only high-K control: `k_values [32,48,64,96]`, `primary_k: 48`, softmax. | Expected to stay weak or negative; confirms larger K dilutes signal. | Low expected payoff; useful only as control after candidate configs. | 20 | No | Yes, with research rerun on current dataset |

## Recommended Execution Plan

### Stage A: Current-artifact diagnostics

Run without waiting for new data:

1. Regime flip-cooldown sensitivity.
2. KNN small-K softmax sweep.
3. KNN observed-core feature subset.
4. Regime posterior and entropy threshold sweeps.
5. KNN price-trend-WT3D subset.
6. Meta threshold diagnostic ladder.
7. Apply Monitoring red/yellow/green thresholds to every run.

Purpose: identify whether the current failure is mostly no-trade policy, KNN geometry, or meta thresholding. These are diagnostic only because the dataset and label artifacts have known quality gaps.

### Stage B: New data and label regeneration

Run before making any performance claim:

1. Data regeneration with exchange-context quality gates.
2. Label regeneration with full cost, exit, horizon, MFE/MAE, and barrier audit fields.
3. Re-run the best Stage A configs on the regenerated dataset.

Purpose: convert the research package from contract-ready to performance-testable. Without this step, positive expectancy and horizon stability remain insufficiently supported.

### Stage C: Implementation-backed experiments

Run only after Stage A shows a promising direction:

1. Distance-quality gate.
2. Candidate-conditioned meta training.
3. Per-regime pool-size gates.
4. Compatible-regime fallback.

Purpose: avoid adding schema and model complexity until current config-only experiments identify the highest-value failure mode.

## Acceptance Readout Template

Every experiment result should report:

- Artifact manifest path.
- Dataset path and dataset manifest/quality-gate status.
- KNN trade count, long count, short count, expectancy after fees/slippage/funding, profit factor, positive split ratio, and max single-split PnL share.
- Regime no-trade rate, flip rate, entropy p95, max probability p05, and regime distribution.
- Neighbor quality mean, median, p05, and p95.
- KNN and meta Brier scores plus material calibration bucket errors.
- Feature outage status.
- Promotion status, which must remain `promotion_ready: false` during Phase 1 research.

## Final Recommendation

The highest-ranked work is the Data plus Labeling regeneration pair because the current real BTC run is not performance-accepted and has known missing context and label audit gaps. In parallel, the best cheap diagnostics are Regime flip-cooldown sensitivity and KNN small-K/reduced-feature sweeps because they directly attack the two red monitoring metrics: no-trade/flip rate and neighbor quality.

No experiment in this matrix supports live readiness by itself. All runs remain BTC-only, research-only, observe-only, and non-promotional until a regenerated point-in-time dataset produces stable positive costed expectancy with adequate trade count, split coverage, long/short coverage, and horizon evidence.
