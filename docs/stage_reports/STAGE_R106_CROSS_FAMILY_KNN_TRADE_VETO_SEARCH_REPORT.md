# Stage R106 Cross-Family KNN Trade-Veto Search Report

Date: 2026-06-12
Packet: WPR106-136
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of source selection, feature normalization, KNN parameter
choice, threshold choice, ranking, and selection. May was replayed only after
fixed strict pre-May overlay selection.

## Method

The runner
`data/research/wpr106_136_cross_family_knn_trade_veto_search/scripts/run_wpr106_136_cross_family_knn_trade_veto_search.py`
loads selected source trades from WPR106-130 through WPR106-134, then tests a
causal KNN trade-veto overlay.

Inputs:

- WPR106-130 prior-day level/gap selected pre-May and May trades.
- WPR106-131 volatility term-structure selected pre-May and May trades.
- WPR106-132 multi-horizon trend-state selected pre-May and May trades.
- WPR106-133 cross-symbol lead-lag selected pre-May and May trades.
- WPR106-134 microstructure state-transition selected pre-May and May trades.
- WPR106-96 verified 15m BTCUSDT/ETHUSDT bars and 15m aggTrade-flow
  aggregation.

The source universe has 346 selected candidates. Exact pre-May trade behavior
de-duplication keeps 292 source candidates. Each source trade receives
completed-bar features from the signal bar, not the entry or exit bar.

Feature packs:

- `path_flow`: short return path, range, body, flow, volume, and hour phase.
- `regime_reversal`: slower return, wick/range shape, channel location,
  volatility ratio, choppiness, flow, and weekday phase.

The KNN overlay varies Lorentzian versus Euclidean distance, 64 versus
160-trade lookback, 7 versus 15 neighbors, all-side versus same-side history,
neighbor mean/win-rate thresholds, and daily caps of 1, 3, or 5 trades.

For pre-May rows, each trade can only use earlier source trades whose exit is
complete before the current signal. For May rows, the neighbor history is
frozen to pre-May source trades only. Costs use the inherited taker plus
slippage/spread model: 0.0432% taker fee per side plus 0.0150%
slippage/spread per side, for a 0.001164 round-trip cost. Cost stress tests
1.00x, 1.25x, 1.50x, and 2.00x multipliers.

## Results

Pre-May KNN-veto screen:

- Source candidates loaded: 346.
- Deduped source-pool rows: 292.
- Evaluated overlay rows: 168,192.
- Positive pre-May rows: 132,125.
- Annual-target rows: 25,371.
- Loose pre-May rows: 14,903.
- Strict pre-May rows: 12.
- Unique source candidates among strict rows: 2.
- Fixed selected rows: 12 strict rows.

The top selected strict overlay is:

- Overlay ID: `tradeveto-ab121ee82a5df85e`.
- Source: WPR106-133 `leadlag-1fe0b4f5af35c5e2`.
- Symbol/family: ETHUSDT cross-symbol leader momentum.
- Feature pack: `path_flow`.
- Distance: Lorentzian.
- Lookback: 64 source trades.
- Neighbors: 7.
- History: all sides.
- Thresholds: minimum neighbor mean -0.00010, minimum neighbor win rate 0.48.
- Daily cap: 1 accepted trade.
- Trades: 147.
- Active months: 26.
- Losing months: 5.
- Annual losses: 2024: 2, 2025: 2, 2026 Jan-Apr: 1.
- Pre-May net return: +0.383212.
- Max drawdown: -0.058052.
- Sortino daily: 0.344683.
- Best-month share: 0.144292.
- Cost-stress survival: 4/4.

The selected set is concentrated. All 12 strict rows are parameter variants
around two WPR106-133 ETHUSDT leader-momentum source candidates. Those two
sources accept the same eight May trades after the fixed overlay.

May 2026 benchmark after fixed strict pre-May selection:

- May-positive selected rows: 0.
- May-negative selected rows: 12.
- May-flat selected rows: 0.
- Each selected overlay accepts 8 May trades.
- Best May net return: -0.070820.
- Worst May net return: -0.070820.
- Median May net return: -0.070820.

## Decision

The cross-family KNN trade-veto overlay is rejected as a candidate lead. It can
turn two WPR106-133 ETHUSDT leader-momentum source rows into strict-looking
pre-May overlays, but the evidence is concentrated and the fixed behavior
fails May 2026 decisively. The May loss is not a small flat result: all selected
rows accept the same eight May trades and lose -0.070820 after costs.

Useful follow-up context: trade-level analog vetoes can improve pre-May
monthly stability for some discarded rows, but this implementation mostly
selects one lead-lag cluster. Future work should require source-behavior
diversity before May benchmarking or use the KNN veto as one component in a
broader pre-May-only ensemble selector rather than as a standalone lead.

## Artifacts

- `data/research/wpr106_136_cross_family_knn_trade_veto_search/wpr106_136_cross_family_knn_trade_veto_summary.json`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/pre_may/source_universe.parquet`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/pre_may/source_pool.parquet`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/pre_may/source_pool_trades_pre_and_may.parquet`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/pre_may/knn_trade_veto_ranking.parquet`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/pre_may/knn_trade_veto_top2000.csv`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/pre_may/family_summary.parquet`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_136_cross_family_knn_trade_veto_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
