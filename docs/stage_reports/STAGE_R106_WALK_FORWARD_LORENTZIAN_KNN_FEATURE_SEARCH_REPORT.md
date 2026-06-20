# Stage R106 WPR106-116 Walk-Forward Lorentzian KNN Feature Search Report

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Boundary

WPR106-116 is research-only, observe-only, and promotion-ready false. It is an
artifact-only Lorentzian/KNN runner under
`data/research/wpr106_116_walk_forward_lorentzian_knn_feature_search/`.
It does not change shared package code, registries, feature builders, backtest
engines, candidate-pack logic, live configuration, runtime mode, or sizing
behavior.

Every feature-pack, label horizon, lookback, neighbor count, train spacing,
score threshold, side mode, session/regime filter, max trades/day cap, rank,
and selection decision uses only 2024-01-01 through 2026-04-30. May 2026 is
used only as a benchmark holdout after fixed pre-May rows are selected.

CUDA was not used and no speedup claim is made.

## Method

The runner is:

`data/research/wpr106_116_walk_forward_lorentzian_knn_feature_search/scripts/run_wpr106_116_walk_forward_lorentzian_knn_feature_search.py`

Inputs are the WPR106-96 verified 15m feature frames:

- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/features/btcusdt_features_price_trend_vol_2024_01_to_2026_05.parquet`
- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/features/ethusdt_features_price_perp_aggflow_no_wt_2024_01_to_2026_05.parquet`

Labels are built inside the runner from next-bar entries to future close at
8, 16, and 32 15m-bar horizons. Query rows are sampled every 8 bars. For each
query row, all neighbors must have labels completed before the query signal
time. Feature matrices are normalized by pre-May median/IQR and clipped to
bound outliers.

Feature packs:

- `price_path_vol`: returns, path z-score, range width, volatility, ATR
  percentile, and volatility shock.
- `trend_pullback_state`: momentum, trend slope, directional pressure,
  pullback position, efficiency, and choppiness.
- `wick_range_shape`: OHLC-derived wick ratios, close location, range width,
  volatility, and choppiness.
- `price_flow_proxy`: returns, taker-flow proxy imbalance, quote-volume
  z-score, flow/price alignment, ATR percentile, and volatility shock.

The search varies lookback length, neighbor count, horizon, score threshold,
side mode, session, regime, and max trades/day. Costs are 0.0432% taker fee
plus 0.0150% slippage/spread per side. One-position overlap and max trades/day
caps are enforced.

## Artifacts

Root:

`data/research/wpr106_116_walk_forward_lorentzian_knn_feature_search/`

Key pre-May artifacts:

- `pre_may/walk_forward_knn_ranking.parquet`
- `pre_may/walk_forward_knn_top2000.csv`
- `pre_may/walk_forward_knn_monthly_returns.parquet`
- `pre_may/selected_pre_may.parquet`
- `pre_may/selected_pre_may_replay_metrics.parquet`
- `pre_may/selected_pre_may_trades.parquet`
- `pre_may/selected_pre_may_monthly_returns.parquet`
- `pre_may/selected_pre_may_daily_returns.parquet`

Key May benchmark artifacts:

- `may_benchmark/selected_may_benchmark_metrics.parquet`
- `may_benchmark/selected_may_benchmark_trades.parquet`
- `may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `may_benchmark/selected_may_benchmark_daily_returns.parquet`

Summary:

- `wpr106_116_walk_forward_lorentzian_knn_feature_search_summary.json`

## Results

Rows evaluated: 41,472.

Pre-May screen:

- Positive pre-May rows: 4,219.
- Loose pre-May rows: 231.
- Strict pre-May rows: 0.
- Positive annual-target rows with no more than 2/2/1 losing months in
  2024/2025/2026 Jan-Apr: 63.
- Annual-target rows with at least 40 trades and at least 10 active months:
  32.

The 32 active-ish annual-target rows are still blocked:

- 32 of 32 have fewer than 20 active months.
- 29 of 32 have fewer than 80 trades.
- 14 of 32 have best-month PnL share above 0.45.
- None are blocked by drawdown or total losing-month count.

Selected set:

- Selected rows: 80 loose rows.
- Unique selected symbol/feature-pack/horizon groups: 21.
- Selected losing months: min 5, median 7, max 10.
- Selected rows satisfying the annual target: 2.

Top selected pre-May row:

- Candidate: `wfknn-dd0a460e7ba2426e`.
- Symbol/pack: BTCUSDT `price_path_vol`.
- Parameters: Lorentzian distance, 960-bar lookback, 31 neighbors, 32-bar
  horizon, long-only, Asia session, trend regime, one trade/day cap.
- Pre-May return: +0.323736 after costs.
- Trades: 45.
- Active months: 17.
- Losing months: 6.
- Annual losses: 2024: 3, 2025: 3, 2026 Jan-Apr: 0.
- Max drawdown: -0.018922.
- Cost-stress survival: 1.0.
- Rolling losing blocks: 0.

Best annual-target active-ish row:

- Candidate: `wfknn-bead0446e2412fcb`.
- Symbol/pack: ETHUSDT `trend_pullback_state`.
- Parameters: Lorentzian distance, 2,880-bar lookback, 31 neighbors, 32-bar
  horizon, long-only, Asia session.
- Pre-May return: +0.304182.
- Trades: 86.
- Active months: 18.
- Losing months: 5.
- Annual losses: 2024: 2, 2025: 2, 2026 Jan-Apr: 1.
- Max drawdown: -0.127323.
- Cost-stress survival: 1.0.
- Blocker: fewer than 20 active months.

May benchmark after fixed pre-May selection:

- May-positive selected rows: 6.
- May-negative selected rows: 15.
- May-flat selected rows: 59.
- Best selected May return: +0.008076.
- Worst selected May return: -0.033921.

The best selected May rows are ETHUSDT `trend_pullback_state` variants with
only one May trade and 9 losing pre-May months. The two selected annual-target
rows have 0 May trades. The large May-flat count therefore represents missing
May participation, not confirmation.

## Interpretation

This packet tests the KNN family with a different mechanism from the prior
configuration: causal walk-forward neighbor pools, pre-May-only robust feature
normalization, OHLC-derived wick/range features, price/flow proxy features,
active-rate thresholding, and explicit overlap/day-cap handling. It finds
more plausible annual-stability diagnostics than the WPR106-115 direct
regime-switch search, including rows near the desired annual loss profile.

It still does not produce a candidate-ready lead. No strict row exists. The
annual-target rows either do not trade enough, are active in too few months, or
have concentration concerns. Selected rows with May profits are too small in
May participation and were not pre-May stable enough.

No candidate pack, paper/live artifact, order placement, sizing change,
runtime-mode change, live configuration write, CUDA speedup claim, or promotion
claim exists.

## Validation

Passed:

```powershell
python -m compileall -q data/research/wpr106_116_walk_forward_lorentzian_knn_feature_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
