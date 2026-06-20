# WPR106-92 Lorentzian KNN Temporal Stability Refresh

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Continue the 2024-forward broad search by revisiting Lorentzian/KNN families
after WPR106-86 found small positive rows that were too sparse or too
month-concentrated. Target month-to-month stability directly with feature,
filter, threshold, k, weighting, and regime-pool variants.

Use 2024-01-01 through 2026-04-30 only for tuning, selection, ranking, and
summaries. Keep May 2026 fully out of this packet except as a future benchmark
holdout dependency for any later strict pre-May lead.

## Scope

- Add one scoped no-context KNN feature pack if useful for the current
  archive-backed datasets, using only completed-bar price, wick, volatility,
  and observed aggTrade-flow columns already present in the WPR106-85 pre-May
  four-bar datasets.
- Add focused HMM/KNN feature-pack coverage if a new pack is added.
- Build BTCUSDT and ETHUSDT WPR106-92 experiment specs that revisit WPR106-86
  with more temporal-stability-oriented variants:
  - 1h-to-4h ETH/BTC rows around the prior positive meta cells,
  - 15m-to-1h higher-activity controls,
  - Lorentzian, cosine, and Euclidean robust-z controls,
  - compatible, same-with-all-fallback, and all-regime pools,
  - looser and stricter KNN/meta probability thresholds,
  - inverse-distance, softmax, and uniform weighting.
- Treat 1 to 5 trades per active day as normal when costs, split evidence,
  overlap/activity, and monthly evidence are recorded.
- Summarize KNN and meta rows by net return, expectancy, active days,
  trades per active day, active months, losing months by year, monthly
  concentration, split dominance, and May-holdout eligibility.
- Use CPU multiprocessing and truthful CUDA metadata only. CUDA may be used by
  existing Lorentzian distance backend when selected by the artifact, but this
  packet must not claim a CUDA speedup unless separately proven.

## Allowed paths

- `docs/work_packets/WPR106-92-lorentzian-knn-temporal-stability-refresh.md`
- `docs/stage_reports/STAGE_R106_LORENTZIAN_KNN_TEMPORAL_STABILITY_REFRESH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/strategies/hmm_knn/config.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `configs/research/wpr106_92_*.json`
- `data/research/wpr106_92*/**`

## Out of scope

- No live, paper, shadow, order-placement, position-sizing, runtime-mode, or
  live-configuration changes.
- No candidate pack, promotion artifact, or promotion-ready claim.
- No May 2026 tuning, selection, ranking, or optimizer feedback.
- No new venue/source intake and no synthetic fallback.
- No CUDA speedup claim unless a real CUDA-backed path is measured and written
  as evidence.
- No broad research-cycle, backtest, data-contract, live-boundary, or operator
  UI rewrites.

## Exit evidence

- BTCUSDT config:
  `configs/research/wpr106_92_lorentzian_knn_temporal_stability_btcusdt_v1.json`
- ETHUSDT config:
  `configs/research/wpr106_92_lorentzian_knn_temporal_stability_ethusdt_v1.json`
- BTCUSDT matrix:
  `data/research/wpr106_92_lorentzian_knn_temporal_stability/btcusdt/experiment_manifest.json`
- ETHUSDT matrix:
  `data/research/wpr106_92_lorentzian_knn_temporal_stability/ethusdt/experiment_manifest.json`
- Relocated artifact cache:
  `data/research/wpr106_92_lorentzian_knn_temporal_stability/cache/`
- Summary artifacts:
  `data/research/wpr106_92_lorentzian_knn_temporal_stability/summary/wpr106_92_knn_temporal_stability_summary.json`,
  `data/research/wpr106_92_lorentzian_knn_temporal_stability/summary/wpr106_92_knn_temporal_stability_summary.csv`,
  and
  `data/research/wpr106_92_lorentzian_knn_temporal_stability/summary/wpr106_92_knn_temporal_monthly_returns.csv`.
- Stage report:
  `docs/stage_reports/STAGE_R106_LORENTZIAN_KNN_TEMPORAL_STABILITY_REFRESH_REPORT.md`
- Ledger update.
- Validation baseline passed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_hmm_knn.py -q
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Results:

- HMM/KNN focused suite: 49 passed, 2 existing CUDA/CuPy/XGBoost device
  warnings.
- Compileall: passed.
- Contracts: 454 passed.
