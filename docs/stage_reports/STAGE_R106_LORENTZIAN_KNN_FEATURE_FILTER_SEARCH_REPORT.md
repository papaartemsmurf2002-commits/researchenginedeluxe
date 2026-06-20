# Stage R106 Lorentzian KNN Feature Filter Search Report

Date: 2026-06-11

Work packet:
`docs/work_packets/WPR106-86-lorentzian-knn-feature-filter-search.md`

## Scope

WPR106-86 continues the 2024-forward broad search after WPR106-85. It does
not defend the rejected sparse BTCUSDT side-veto lead. The packet makes one
scoped KNN feature change, then tests 12 BTCUSDT/ETHUSDT KNN variants on the
pre-May 2024-forward archive-backed four-bar datasets.

Tuning/search window:

- start: 2024-01-01 00:00:00 UTC;
- cutoff: 2026-04-30 23:59:59 UTC;
- May 2026: not used.

## Feature And Config Changes

Added registered HMM/KNN feature pack:

- `price_wick_flow_no_context`

The pack keeps completed-bar price path, trend, volatility, wick, range
compression, and observed aggTrade-flow features. It intentionally excludes
unavailable book/perp context such as `top_of_book_imbalance`, `spread_bps`,
and `funding_rate` for the current Binance Vision archive-backed datasets.

Configs:

- `configs/research/wpr106_86_lorentzian_knn_feature_filter_btcusdt_v1.json`
- `configs/research/wpr106_86_lorentzian_knn_feature_filter_ethusdt_v1.json`

The configs test:

- new no-context wick/flow Lorentzian variants on 15m->1h and 1h->4h rows;
- compatible, all-regime, and same-with-all-fallback neighbor pools;
- loose and stricter vote/meta thresholds;
- inverse-distance, softmax, and uniform weighting;
- Euclidean and cosine distance controls.

## Commands

```powershell
$env:PYTHONPATH='src'
python -m tradingbotsuite.main run-hmm-knn-experiments --spec configs\research\wpr106_86_lorentzian_knn_feature_filter_btcusdt_v1.json --output-dir wpr106_86_lorentzian_knn_feature_filter\btcusdt --cache-dir wpr106_86_lorentzian_knn_feature_filter\cache\btcusdt --workers 3 --skip-monitor
python -m tradingbotsuite.main run-hmm-knn-experiments --spec configs\research\wpr106_86_lorentzian_knn_feature_filter_ethusdt_v1.json --output-dir wpr106_86_lorentzian_knn_feature_filter\ethusdt --cache-dir wpr106_86_lorentzian_knn_feature_filter\cache\ethusdt --workers 3 --skip-monitor
```

The initial cache path was relative and was relocated under
`data/research/wpr106_86_lorentzian_knn_feature_filter/cache/` after the run so
all generated evidence sits under the work-packet data root. Manifests were
rewritten to the relocated paths and checked for resolvable artifact paths.

## Outputs

- BTC matrix:
  `data/research/wpr106_86_lorentzian_knn_feature_filter/btcusdt/experiment_manifest.json`
- ETH matrix:
  `data/research/wpr106_86_lorentzian_knn_feature_filter/ethusdt/experiment_manifest.json`
- Relocated artifact cache:
  `data/research/wpr106_86_lorentzian_knn_feature_filter/cache/`
- Stability summary:
  `data/research/wpr106_86_lorentzian_knn_feature_filter/summary/wpr106_86_knn_variant_stability_summary.json`
- Stability CSV:
  `data/research/wpr106_86_lorentzian_knn_feature_filter/summary/wpr106_86_knn_variant_stability_summary.csv`
- Monthly returns CSV:
  `data/research/wpr106_86_lorentzian_knn_feature_filter/summary/wpr106_86_knn_variant_monthly_returns.csv`
- K/weighting sweep summary:
  `data/research/wpr106_86_lorentzian_knn_feature_filter/summary/wpr106_86_knn_variant_sweep_summary.csv`

Both matrices passed research-boundary checks. BTC runtime was 722.903161
seconds with 3 effective workers. ETH runtime was 720.785808 seconds with 3
effective workers.

Lorentzian variants requested `distance_backend: auto` and artifact manifests
record resolved `knn_distance_backend: cupy`. Euclidean and cosine controls ran
on CPU. The runs also emitted a CuPy CUDA-path warning, repeated HMM
convergence/zero-transition warnings, and an XGBoost mismatched-device warning.
Those warnings are recorded as diagnostic; no CUDA speedup claim is made.

## Results

Summary across 12 experiments and 24 primary KNN/meta strategy rows:

| Metric | Value |
| --- | ---: |
| Strategy rows | 24 |
| Positive expectancy rows | 3 |
| Positive net rows | 3 |
| Promising pre-May leads | 0 |
| Rows with May 2026 trades | 0 |

Top primary rows:

| Symbol | Row | Strategy | Trades | Net after costs | Expectancy | Active months | Losing active months | Avg trades/active day | Decision |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| ETHUSDT | 1h 4h wick flow Lorentzian compatible inverse loose | Meta | 228 | +0.035891 | +0.000157 | 10 | 6 | 1.399 | rejected |
| BTCUSDT | 1h 4h wick flow Lorentzian compatible inverse loose | Meta | 27 | +0.030438 | +0.001127 | 4 | 1 | 1.227 | rejected |
| BTCUSDT | 15m 1h wick flow Lorentzian compatible inverse strict | Meta | 8 | +0.001448 | +0.000181 | 5 | 3 | 1.000 | rejected |
| ETHUSDT | 1h 4h wick flow Lorentzian compatible inverse loose | KNN | 922 | -0.074834 | -0.000081 | 12 | 7 | 2.863 | rejected |

The ETHUSDT 1h/4h wick-flow meta row is the only row with enough trades,
positive total net, and positive expectancy to deserve closer inspection. It
still fails the requested stability profile: only 10 active months, 6 losing
active months, and positive PnL concentrated in 2025-07, 2025-08, 2025-10, and
2026-01. Its monthly sequence is not close to the target of roughly 1-2 losing
months per year.

All KNN primary rows remain negative after costs. The best K/weighting sweep
rows are still negative after costs, including the ETHUSDT 1h/4h wick-flow
primary row at 922 trades and -0.000081 expectancy.

## May 2026 Holdout

May 2026 was not used in tuning, selection, or generated rows. No May 2026
benchmark was run because no WPR106-86 row is a promising pre-May lead after
monthly stability review. `ISSUE-R106-025` remains the data dependency if a
later lead survives pre-May gates and needs the benchmark holdout.

## Decision

WPR106-86 rejects the tested KNN variants as pre-May leads. The new no-context
wick/flow feature pack is useful as a cleaner archive-backed feature surface,
but the tested Lorentzian, Euclidean, and cosine variants do not meet the
month-to-month stability target. Active trade rates around 1 to 3 trades per
active day were evaluated and were not rejected for activity alone.

No candidate pack, paper/live artifact, order placement, position sizing,
runtime-mode change, live configuration write, CUDA speedup claim, or promotion
claim was produced.

## Validation

Passed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Results:

- HMM/KNN focused tests: 49 passed, 2 diagnostic environment warnings.
- Contracts: 451 passed.
