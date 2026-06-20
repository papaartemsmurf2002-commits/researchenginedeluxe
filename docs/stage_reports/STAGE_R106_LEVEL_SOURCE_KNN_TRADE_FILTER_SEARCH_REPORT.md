# Stage R106 Level-Source KNN Trade Filter Search Report

Date: 2026-06-12
Packet: WPR106-152
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of WPR106-151 source-pool selection, KNN feature design,
feature normalization, distance metric, lookback, neighbor count, thresholds,
daily-cap choice, ranking, and selection. May was replayed only after fixed
loose pre-May KNN-filter rows were selected.

## Method

The runner
`data/research/wpr106_152_level_knn_trade_filter_search/scripts/run_wpr106_152_level_knn_trade_filter_search.py`
uses WPR106-151 level/retest rows as source strategies and applies a scoped
causal KNN trade-quality filter.

The source pool is selected from WPR106-151 ranking evidence using only
2024-01-01 through 2026-04-30:

- strict/loose WPR106-151 rows;
- active positive annual-target diagnostics;
- high-return active positive rows;
- candidate-id de-duplication before replay;
- exact accepted-trade behavior de-duplication after replay;
- at least 60 pre-May source trades.

The final source pool has 94 rows and 14,495 pre-May source trades. Each source
trade receives completed signal-bar features; no entry, exit, or May label is
used for feature construction.

KNN feature packs:

- `level_score_flow`: WPR106-151 score strength, score sign, flow alignment,
  trend alignment, range, volume, and hour phase.
- `path_level`: short return path, range/body/wick shape, close location,
  level-score strength, flow alignment, and hour phase.
- `regime_level`: slower return, channel position, realized-volatility ratio,
  choppiness, level score context, flow/trend alignment, and weekday phase.

The grid covers:

- Distance metrics: Lorentzian and Euclidean.
- Lookbacks: 48, 96, and 192 source trades.
- Neighbors: 5, 11, and 23.
- History scope: all-side and same-side.
- Minimum neighbor mean: -0.00010, 0.00000, and 0.00035.
- Minimum neighbor win rate: 0.48, 0.54, and 0.60.
- Accepted-trade daily caps: 1, 3, and 5.

Pre-May KNN history is causal: a trade can use only earlier source trades whose
exits completed before the current signal. May uses frozen pre-May source
history only.

## Results

Source pool:

- WPR106-151 source candidate rows considered: 160.
- Source universe rows replayed: 160.
- Behavior-deduped source-pool rows with at least 60 pre-May trades: 94.
- Source-pool pre-May trades: 14,495.
- Source-pool May trades: 203.

KNN overlay grid:

- Evaluated rows: 274,104.
- Positive pre-May rows: 252,394.
- Positive annual-target rows: 69,210.
- Loose rows: 16,568.
- Strict rows: 0.
- Selected rows: 100 loose rows.

Selected pre-May rows:

- Unique selected source rows: 5.
- Feature-pack split: `path_level`: 87, `regime_level`: 10,
  `level_score_flow`: 3.
- Distance split: Lorentzian: 84, Euclidean: 16.
- Selected net-return range: +0.588700 to +0.877616.
- Selected trade-count range: 61 to 97.
- Selected active-month range: 20 to 25.
- Selected losing-month range: 3 to 5.

The top selected loose row is:

- Overlay: `levelknn-be498c291c51f6e9`.
- Source: `wpr151:multilevel-7a1e7f47c5e53657`.
- Symbol/family: ETHUSDT prior-day breakout follow.
- Feature pack: `path_level`.
- Distance: Lorentzian.
- Lookback: 96 source trades.
- Neighbors: 5.
- History: all-side.
- Thresholds: minimum neighbor mean -0.00010, minimum neighbor win rate 0.48.
- Daily cap: 1 accepted trade.
- Trades: 85.
- Active months: 25.
- Losing months: 4.
- Annual losses: 2024: 1, 2025: 2, 2026 Jan-Apr: 1.
- Pre-May net return: +0.877616.
- Max drawdown: -0.132155.
- Best-month share: 0.185848.
- Cost-stress survival: 4/4.

May 2026 benchmark after fixed loose pre-May selection:

- May-positive selected rows: 0.
- May-negative selected rows: 100.
- May-flat selected rows: 0.
- Best May return: -0.002536.
- Worst May return: -0.030063.
- Median May return: -0.016714.

The selected May failure is source-concentrated. The 100 selected rows use only
five source rows, all ETHUSDT prior-day breakout-follow variants. Each selected
source group is May-negative; the largest group has 61 selected parameter
variants and a median May return of -0.017933.

## Decision

The level-source KNN trade filter is rejected as currently configured. It
creates many positive and loose pre-May rows but no strict rows, and May 2026
rejects every fixed selected row. The result does not support a candidate-ready,
paper-ready, live-ready, or promotion-ready claim.

Useful follow-up context: this packet explicitly tested a scoped
Lorentzian/KNN code/feature/parameter variant away from the old WPR106-146
side-veto lineage. Level-aware score, flow, path, and regime KNN features do
not rescue the WPR106-151 level/retest diagnostics. Future KNN work should
prefer a materially different source universe or direct model training target,
not another parameter sweep around these ETHUSDT prior-day breakout sources.

## Artifacts

- `data/research/wpr106_152_level_knn_trade_filter_search/wpr106_152_level_knn_trade_filter_summary.json`
- `data/research/wpr106_152_level_knn_trade_filter_search/pre_may/source_candidate_rows.parquet`
- `data/research/wpr106_152_level_knn_trade_filter_search/pre_may/source_universe.parquet`
- `data/research/wpr106_152_level_knn_trade_filter_search/pre_may/source_pool.parquet`
- `data/research/wpr106_152_level_knn_trade_filter_search/pre_may/source_pool_trades_pre_and_may.parquet`
- `data/research/wpr106_152_level_knn_trade_filter_search/pre_may/level_knn_trade_filter_ranking.parquet`
- `data/research/wpr106_152_level_knn_trade_filter_search/pre_may/level_knn_trade_filter_top2000.csv`
- `data/research/wpr106_152_level_knn_trade_filter_search/pre_may/family_summary.parquet`
- `data/research/wpr106_152_level_knn_trade_filter_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_152_level_knn_trade_filter_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_152_level_knn_trade_filter_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_152_level_knn_trade_filter_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_152_level_knn_trade_filter_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_152_level_knn_trade_filter_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_152_level_knn_trade_filter_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_152_level_knn_trade_filter_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_152_level_knn_trade_filter_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_152_level_knn_trade_filter_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
