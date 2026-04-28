# Feature Agent Phase 1 Readiness Docs

## Agent

Feature Agent

## Task Received

Produce final Phase 1 readiness packaging in Markdown only. Include implemented work, synthetic fixture validation, real BTC validation if available, failed gates, insufficient-data gates, Phase 2 ETH notes, and the continuing research-only boundary.

## Files Read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_RUNBOOK.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_SOURCE_LOG.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_mid_development_readiness_scorecard.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_cli_e2e_fixture_validation.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_real_btc_dataset_inventory.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_real_btc_contract_run.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_real_btc_acceptance_triage.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_regime_agent_real_btc_regime_review.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_real_btc_neighbor_review.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_meta_model_agent_real_btc_meta_review.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_real_btc_monitoring_review.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_labeling_agent_real_btc_label_quality.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_real_data_readiness_boundary.md`

## Files Changed

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_feature_agent_phase1_readiness_docs.md`

## Implemented

- BTC-only HMM Multi-KNN research config and artifact contract.
- `research-hmm-knn`, `replay-hmm-knn`, and observe-only `monitor-hmm-knn` CLI paths.
- Dataset, label, WT3D feature, HMM regime, Lorentzian KNN, meta-model, walk-forward metrics, replay, monitoring, operator UI summary, and public contract documentation surfaces.
- Artifact handoff protocol under `docs/tradingbotsuite_runtime/agent_artifacts/`.
- Public contract freeze notes for dataset manifests, HMM/KNN manifests, parquet/CSV outputs, metrics, and monitoring reports.

## Validated By Synthetic Fixture

- CLI/E2E fixture validation is implemented and green.
- The fixture runs `research-hmm-knn` followed by `monitor-hmm-knn` through `python -m tradingbotsuite.main`.
- The fixture uses synthetic BTC data under pytest `tmp_path`, avoids live exchange calls, verifies expected artifacts, and keeps generated artifacts outside repo data directories.
- The fixture verifies `monitoring_report.json` flags:
  - `research_only: true`
  - `observe_only: true`
  - `promotion_ready: false`
- Synthetic fixture and smoke artifacts validate command paths, schema, metadata, diagnostics, and observe-only monitoring. They do not validate profitability or live readiness.

## Validated By Real BTC If Available

Real BTC data was available locally.

- Data Agent identified `data/research/v2-btc-research-1/btcusdt_dataset.parquet` as usable for local HMM/KNN Phase 1 artifact generation.
- The dataset had `1173` rows, `105` columns, `BTCUSDT` only, configured KNN feature columns, HMM emission features, labels, and missingness columns.
- Caveat: the local dataset is consumable by HMM/KNN but predates stricter current raw exchange-context audit fields and manifest summaries.
- Backtest Agent ran the real local BTC HMM/KNN command path and wrote artifacts under `data/research/v2-btc-hmm-multi-knn-1`.
- The real BTC run produced `446` evaluation rows, with manifest `research_only: true` and metrics `promotion_ready: false`.
- Monitoring report remained `research_only: true`, `observe_only: true`, and `promotion_ready: false`.
- Regime review found all four regimes present in the real BTC artifact, including `range_chop` and `shock_transition`, but also warned not to treat the regime layer as stable because it flips too often.

## Failed Gates

- Positive expectancy after fees, slippage, and funding failed.
  - Pure KNN expectancy after cost: `-1.0008811453163364`.
  - Meta accepted zero trades, so it provides no positive expectancy evidence.
- Minimum trade count failed.
  - Pure KNN trades: `5` versus required `25`.
  - Meta trades: `0` versus required `25`.
- Positive split ratio failed at `0.0`.
- Split concentration failed for KNN.
  - KNN max single split PnL share exceeded the configured limit.
- Meta long/short breakout failed.
  - Meta accepted `0` long and `0` short trades.
- KNN neighbor quality was weak in the real BTC artifact; all sweep combinations were evaluated and none showed positive expectancy after cost.

## Insufficient-Data Gates

- Meta split concentration is insufficient-data because zero accepted meta trades cannot validate concentration.
- Horizon stability across `6h`, `24h`, and `72h` is insufficient-data because the real artifact does not include separate realized metrics by horizon.
- The `7d` exploratory horizon is insufficient-data for the same reason.
- Real BTC label-quality review found the saved artifacts credible for coarse HMM/KNN contract execution only, not exact label accounting.
- Saved real BTC artifacts cannot verify exact exit timestamps, time-to-exit distributions, purge/embargo based on realized label windows, or MFE/MAE stopping at the actual exit bar.
- Monitoring live-vs-replay mismatch remains `not_available`; real live/replay comparison data is not present.

## Phase 2 ETH Notes

- ETH remains Phase 2.
- Current schemas keep `asset_scope` extensible, but Phase 1 implementation, dataset validation, synthetic fixture validation, and real-data evidence are BTC-only.
- ETH work requires a separate assignment covering ETH data inventory, point-in-time dataset generation, label validation, artifact validation, acceptance triage, monitoring review, and live-boundary review.
- No ETH data or ETH live behavior should be inferred from the BTC Phase 1 artifacts.

## Still Research-Only

- No positive expectancy claim exists.
- No live-readiness claim exists.
- Current real BTC evidence is negative or insufficient for promotion.
- All HMM/KNN artifacts remain research-only and non-promotional.
- HMM/KNN artifact fields must not feed live gates, live sizing, Hyperliquid execution, safety behavior, runtime-mode switching, or operator live controls without a separate explicit approval pass.

## Validation Notes

- No Python or test files were changed.
- No tests were run because this task was Markdown-only.
- The realization plan was updated so public docs include the same Phase 1 readiness packaging captured here.

## Open Issues

- Regenerate a current-contract BTC dataset before any stricter performance or label-quality claim.
- Add per-horizon realized metrics if horizon stability across `6h`, `24h`, and `72h` remains an acceptance gate.
- Continue treating the real BTC artifact as research-contract and negative/diagnostic evidence, not as promotion evidence.
