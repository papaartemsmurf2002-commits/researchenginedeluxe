# HMM Multi-KNN Realization Plan

Date: April 28, 2026

## Thesis

The production research direction is not a single Lorentzian KNN strategy.

The target architecture is:

```text
HMM regime router -> regime-specific Lorentzian KNN -> XGBoost meta-filter -> triple-barrier exit research
```

The HMM classifies market state. The KNN answers whether similar historical conditions inside that state produced favorable path-dependent outcomes. The meta-filter decides whether the KNN signal is tradable after regime, perp, WT3D, and cost context are included.

Phase 1 is BTC-only and research-only. ETH support is designed into schemas through `asset_scope`, but ETH data, validation, and live behavior are deferred until BTC results are stable.

## Phase Order

1. **Research baseline integration**
   - Add `configs/v2_btc_hmm_multi_knn_research.json`.
   - Add `research-hmm-knn`, `replay-hmm-knn`, and observe-only `monitor-hmm-knn` CLI commands.
   - Keep all artifacts under `data/research/<plan_version>/`.
   - Keep normal runtime, live gating, and Hyperliquid execution unchanged.

2. **Regime layer**
   - Fit the regime model only on walk-forward train rows.
   - Emit posterior probabilities, entropy, top regime, recent-flip flag, and no-trade flag.
   - Use posterior confidence instead of only hard Viterbi state.
   - Skip or reduce confidence when posterior probability is below `0.60`, entropy is high, or the state has flipped recently.

3. **Feature layer**
   - Reuse the existing BTC V2 dataset and feature columns.
   - Add WT3D-derived features as bounded state descriptors: fast, normal, slow, spreads, slope, acceleration, cross age, reversal intensity, and MTF agreement.
   - Keep perp and microstructure features first-class: funding, basis, OI change, taker imbalance, queue imbalance, spread, and volatility shock.

4. **Regime-local KNN**
   - Train KNN over robust-z feature space.
   - Use Lorentzian distance:

```text
D(x, y) = sum(log(1 + abs(x_i - y_i) / scale_i))
```

   - Search only same-regime neighbors by default.
   - Output probability and diagnostics, not direct orders: `p_up_barrier`, `p_down_barrier`, `expected_net_return_after_costs`, `neighbor_agreement`, and `neighbor_distance_quality`.

5. **Meta-filter and evaluation**
   - Use XGBoost as the selected first meta-labeler when the research extra is installed.
   - Use deterministic fallback modeling only to keep default tests and environments runnable.
   - Compare pure KNN against the meta-filter and existing V2 baseline style metrics.
   - Report walk-forward stability, split concentration, long/short breakout, and research-only promotion failures.

## Acceptance Criteria

- Walk-forward expectancy is positive after fees, slippage, and funding.
- No single split or month dominates PnL.
- Long and short outcomes are reported separately.
- Results are stable across `6h`, `24h`, and `72h`; `7d` remains exploratory until more samples exist.
- Feature importance is not dominated by leakage-prone fields.
- Shock regime mostly prevents bad trades rather than adding leverage.
- Every artifact and metric explicitly reports `research_only: true`.
- Monitoring artifacts explicitly report `observe_only: true` and `promotion_ready: false`.

## Final Validation And Smoke Status

- Repo-wide pytest collection uses `addopts = "--import-mode=importlib"` in `pyproject.toml` to avoid duplicate test module basename collisions between the top-level `tests/` tree and `tests/tradingbotsuite/`.
- Mid-development full-suite validation passed with `$env:PYTHONPATH='src'; python -m pytest -q` and reported `383 passed in 146.44s`.
- Targeted HMM/KNN, research, and operator UI validation is green at `56 passed in 21.74s`.
- CLI/E2E fixture validation is green: it runs `research-hmm-knn` followed by `monitor-hmm-knn` through `python -m tradingbotsuite.main`, uses synthetic BTC data under `tmp_path`, verifies the expected artifact files, and confirms `monitoring_report.json` remains `research_only: true`, `observe_only: true`, and `promotion_ready: false`.
- A synthetic BTC HMM/KNN CLI smoke artifact was generated with `research-hmm-knn` using the production config and a temporary synthetic dataset.
- Regime, KNN, and Meta agents audited the smoke artifact outputs for posterior/no-trade fields, same-regime diagnostics, K sweep fields, backend/fallback reporting, comparison metrics, and explicit promotion failures.
- The Monitoring Agent ran `monitor-hmm-knn --manifest <artifact_manifest.json>` against the smoke artifact and generated observe-only `monitoring_report.json`.
- The smoke monitoring report preserved `research_only: true`, `observe_only: true`, and `promotion_ready: false`.
- The readiness scorecard treats the current state as mid-development research-contract validation only. It makes no positive expectancy or live-readiness claim.

## Phase 1 Readiness Packaging

Implemented:

- BTC-only HMM Multi-KNN research config, CLI commands, artifact schema, replay path, observe-only monitoring path, public contract docs, and agent handoff artifacts.
- Feature, labeling, regime, KNN, meta-model, backtest, monitoring, and operator UI research surfaces are present for Phase 1 contract validation.

Validated by synthetic fixture:

- CLI/E2E fixture validation runs `research-hmm-knn` followed by `monitor-hmm-knn` through `python -m tradingbotsuite.main`.
- The fixture uses synthetic BTC data under `tmp_path`, verifies all expected research artifacts, and verifies `monitoring_report.json` remains `research_only: true`, `observe_only: true`, and `promotion_ready: false`.
- Synthetic fixture and smoke artifacts validate command paths, schema, metadata, diagnostics, and observe-only monitoring behavior only. They do not validate profitability.

Validated by real BTC if available:

- A local BTC dataset was available at `data/research/v2-btc-research-1/btcusdt_dataset.parquet` and was classified as usable for local HMM/KNN Phase 1 artifact generation.
- A real local BTC HMM/KNN research run produced artifacts under `data/research/v2-btc-hmm-multi-knn-1` with `446` evaluation rows, `research_only: true`, and `promotion_ready: false`.
- The real BTC command path works end-to-end, but it is negative diagnostic evidence rather than acceptance evidence.

Failed gates:

- Positive expectancy after fees, slippage, and funding failed: pure KNN expectancy after cost was `-1.0008811453163364`; the meta-filter accepted zero trades.
- Minimum trade count failed: pure KNN had `5` trades versus the required `25`, and meta had `0` trades.
- Positive split ratio failed at `0.0`.
- Split concentration failed for KNN; max single split PnL share exceeded the configured limit.
- Meta long/short breakout failed because meta accepted no long or short trades.

Insufficient-data gates:

- Meta split concentration is insufficient-data because zero accepted meta trades cannot validate concentration.
- Horizon stability across `6h`, `24h`, and `72h` is insufficient-data because the real artifact does not contain separate realized metrics by horizon.
- The `7d` exploratory horizon is insufficient-data for the same reason.
- Label-quality review found the saved real BTC artifacts credible for coarse contract execution only, not exact label accounting, realized exit timing, or MFE/MAE distribution claims.

Phase 2 ETH notes:

- ETH remains Phase 2. Current schema keeps `asset_scope` extensible, but Phase 1 code, dataset validation, and readiness evidence are BTC-only.
- ETH requires a separate assignment with ETH data inventory, dataset generation, artifact validation, acceptance triage, and live-boundary review.

Still research-only:

- No positive expectancy claim exists.
- No live-readiness claim exists.
- HMM/KNN artifacts must not feed live gates, live sizing, Hyperliquid execution, safety behavior, runtime-mode switching, or operator live controls without a separate explicit approval pass.

## Architecture Gap Triage

Continuation orchestration converted the real BTC run into explicit architecture-gap evidence:

- Regime routing emits all four intended labels, but recent regime flips are very frequent (`0.8946`) and the regime no-trade rate is high (`0.9103`). The regime layer is currently defensive rather than tradable.
- Same-regime Lorentzian KNN diagnostics are populated and same-regime-only, but KNN accepted only `5` trades, mean distance quality is low (`0.1555`), and costed expectancy is negative.
- The meta-filter used `random_forest_fallback` because XGBoost is unavailable in the current environment; it accepted zero trades, so it validates schema/backend reporting but not edge.
- Monitoring maps the main risks through observe-only alerts: `high_no_trade_rate` and `low_neighbor_quality`.
- The real BTC dataset is usable for coarse diagnostic replay, but important perp/microstructure context is missing or sparse. Exact label-distribution claims require regenerating the dataset with the latest hardened label/context manifest.

Next research iteration should focus on data quality, longer history, regime stability, and neighbor pool quality before threshold tuning or any live-promotion discussion.

## Next Experiment Matrix Summary

All next experiments are offline research only. They must use cloned research configs, local or explicitly authorized historical datasets, temp or explicit research output directories, and must keep `research_only: true`, `promotion_ready: false`, and monitoring `observe_only: true`. No experiment may feed HMM/KNN outputs into live gates, sizing, Hyperliquid execution, safety behavior, runtime-mode switching, or operator live controls.

Selected execution stages:

| Stage | Priority | Experiments | Purpose | Boundary |
| --- | --- | --- | --- | --- |
| A | Current-artifact diagnostics | Regime flip-cooldown sensitivity; KNN small-K softmax sweep; KNN observed-core feature subset; posterior and entropy threshold sweeps; KNN price-trend-WT3D subset; meta threshold diagnostic ladder; monitoring red/yellow/green overlay. | Identify whether current failure is mostly no-trade policy, KNN geometry, or meta thresholding. | Offline research reruns or artifact diagnostics only; no live gates or acceptance semantics change. |
| B | Data and label regeneration | Regenerate BTC dataset with exchange-context quality gates; regenerate labels with full triple-barrier audit fields; re-run the best Stage A configs on regenerated data. | Convert the package from contract-ready to performance-testable by fixing missing context, label audit, and horizon evidence gaps. | Data regeneration must be local/offline or explicitly authorized historical extraction; current-only websocket/order-book state must not backfill historical rows. |
| C | Implementation-backed experiments | Distance-quality gate; candidate-conditioned meta training; per-regime pool-size gates; bounded compatible-regime fallback. | Add schema/model complexity only after config-only diagnostics identify a high-value failure mode. | Research code/config only; outputs remain non-promotional and must extend manifests/metrics/diagnostics for auditability. |

Highest-ranked items from the matrix:

1. Regenerate BTC dataset with exchange-context quality gates.
2. Regenerate labels with full triple-barrier audit fields.
3. Regime flip-cooldown sensitivity.
4. KNN small-K softmax sweep.
5. KNN observed-core feature subset.
6. Regime posterior threshold sensitivity.
7. Regime entropy threshold sensitivity.
8. KNN price-trend-WT3D subset.
9. Meta threshold diagnostic ladder.
10. Monitoring red-to-yellow acceptance overlay.

Experiment readouts must report manifest path, dataset and quality-gate status, KNN trade count, long/short counts, costed expectancy, profit factor, split concentration, regime no-trade and flip rates, entropy and posterior diagnostics, neighbor quality distribution, calibration, feature outages, and explicit `promotion_ready: false`.

## Production Risks

- Regime labels can drift after each refit; use posterior confidence and label-by-statistics rather than fixed component IDs.
- HMM outputs must not use future-smoothed Viterbi states in live-style scoring.
- WT3D divergence and pivot features can leak future data if implemented naively; Phase 1 uses only completed-bar, non-pivot features.
- Funding, OI, and premium data must be point-in-time aligned. Missing values must remain explicit missingness.
- KNN can overfit via neighbor memorization; all comparisons must be purged walk-forward with embargo.
- The meta-model can hide weak KNN behavior; report pure KNN metrics beside meta-filter metrics.
- Phase 1 artifacts remain research-only even when validation is green; a separate approval pass is required before any live execution, sizing, gate, Hyperliquid, safety, or operator live-control integration.

## Critical Audit Reprioritization

The uploaded April 28, 2026 critical audit and BTC/ETH architecture review add a stricter orchestration priority. They do not make the current HMM/KNN package live-ready. They explicitly classify the branch as a research prototype with failed promotion evidence:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- BTC-only implementation
- sparse real BTC evidence (`446` rows)
- pure KNN accepted only `5` trades
- costed KNN expectancy around `-1.0008811453163364`
- meta accepted `0` trades

The next development direction is therefore not threshold tuning or more oscillator variants. The priority order is:

1. Live-readiness safety surfaces and canonical preflight rules.
2. Binance and Hyperliquid event journals with deterministic replay.
3. Point-in-time feature availability, train-only scaling/imputation, and no silent zero-fill.
4. Executable-entry, cost-aware CUSUM/triple-barrier labeling with label-window-aware purge/embargo.
5. HMM posterior routing as diagnostics and no-trade context.
6. KNN as regime-local similarity diagnostics with explicit pool-quality failures.
7. Meta-model ablation after data, labels, and OOF KNN diagnostics are credible.
8. Shadow-mode monitoring and live-vs-replay verification before any future promotion.

Any future live-production branch must prove these safety invariants before HMM/KNN artifacts can matter:

- LIVE cannot start with disabled/zero hard risk caps.
- LIVE cannot run research jobs, even when flat.
- `research_only` or `observe_only` artifacts cannot be loaded as live signals.
- BTC-only artifacts cannot be used for ETH.
- Binance signal prices cannot be treated as Hyperliquid fill prices.
- Hyperliquid order flow requires deterministic `cloid`, order/fill journals, cancel-by-cloid, reduce-only exits, dead-man cancel, and exchange reconciliation.
- Root launchers must call canonical CLI/preflight logic and preserve every config field.
- Default webhook secrets must fail live/external startup checks.

For HMM/KNN research to become worth evaluating as model evidence, future datasets should target at least `10000` event rows per asset, `1000` rows per regime, `300` labeled trades per side per asset, `50` accepted trades per validation split, and `6` walk-forward splits. These are evidence floors, not promotion criteria.
