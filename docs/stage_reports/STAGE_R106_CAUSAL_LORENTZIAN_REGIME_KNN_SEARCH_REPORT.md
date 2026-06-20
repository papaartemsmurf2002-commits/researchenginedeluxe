# Stage R106 Causal Lorentzian Regime KNN Search Report

Date: 2026-06-12
Packet: WPR106-155
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of feature-pack choice, distance metric choice, lookback,
neighbor count, KNN filter, side mode, threshold, daily cap, throttle, ranking,
and selection. May was replayed only after fixed loose pre-May rows were
selected. May KNN labels were frozen to rows whose fixed-hold labels completed
before 2026-05-01.

## Method

The runner
`data/research/wpr106_155_causal_lorentzian_regime_knn_search/scripts/run_wpr106_155_causal_lorentzian_regime_knn_search.py`
loads WPR106-96 BTCUSDT/ETHUSDT 15m bars through the WPR106-151/WPR106-126
context helper, which joins the 1m aggTrade context into completed 15m
flow-imbalance features. Each symbol has 84,672 15m bars from 2024-01-01
through 2026-05-31.

For each signal row, the KNN score uses only prior rows whose candidate
fixed-hold labels have completed before the current signal row. For May replay,
the neighbor-label pool is capped at pre-May labels; no May label can enter the
analog history.

Feature packs:

- `target_regime`: target returns, trend, realized volatility, range, volume,
  target flow, and flow momentum.
- `path_session`: short path returns, close position, range, hour, and weekday.
- `cross_flow_regime`: target regime plus opposite-symbol return/trend/flow,
  relative return, and target-versus-leader flow gap.

The grid covers:

- Symbols: BTCUSDT and ETHUSDT.
- Fixed holds: 8, 16, and 32 bars.
- Lookbacks: 192 and 768 bars.
- Neighbor counts: 11 and 31.
- Distances: Lorentzian primary and Euclidean control.
- Sessions: all and US.
- KNN filters: all, win-rate at least 55%, win-rate at least 60%, and edge
  ratio at least 0.20.
- Side modes: both, long-only, and short-only.
- Target raw signals: 1, 3, and 5 per day.
- Accepted-trade daily caps: 1, 3, and 5.
- Loss-throttle modes: none and skip after one prior completed losing month.

Costs use the same research fee/slippage model as recent packets: 0.0432%
taker fee per side plus 0.0150% slippage/spread per side, for 0.001164
round-trip cost. Cost stress tests 1.00x, 1.25x, 1.50x, and 2.00x cost
multipliers through the reused WPR106 monthly metrics.

Compute used causal online KNN loops over cached numpy feature arrays. No CUDA
path was used, and no speedup was claimed.

## Results

Full pre-May grid:

- Evaluated rows: 62,208.
- Positive pre-May rows: 3,279.
- Positive annual-target rows: 0.
- Loose rows: 219.
- Strict rows: 0.
- Selected rows: 100 loose rows.

Selected pre-May rows:

- Net-return range: +0.294902 to +0.566516.
- Trade-count range: 120 to 407.
- Active-month range: 20 to 28.
- Losing-month range: 6 to 8.
- No selected row meets the annual stability target.

The top selected row is:

- Candidate: `regknn-c61736f1db91ecc3`.
- Symbol: ETHUSDT.
- Family/template: causal Lorentzian regime KNN / online regime KNN.
- Feature pack: `target_regime`.
- Distance: Lorentzian.
- Hold: 32 bars.
- Lookback: 192 bars.
- Neighbor count: 31.
- Session: all.
- KNN filter: all.
- Side mode: both.
- Target raw signals: 3 per day.
- Accepted-trade daily cap: 3.
- Loss throttle: skip after one prior completed losing month.
- Trades: 266.
- Active months: 20.
- Losing months: 8.
- Annual losses: 2024: 4, 2025: 3, 2026 Jan-Apr: 1.
- Pre-May net return: +0.566516.
- Max drawdown: -0.198995.
- Best-month share: 0.211757.
- Cost-stress survival: 4/4.

The best annual-loss diagnostic rows still fail the requested annual stability
target. The closest positive profiles have 2024/2025/2026 losing-month counts
of 2/3/1 or worse. There are zero positive rows with annual losses at or below
2/2/1 and zero positive rows with at least 24 active months and at most 5 total
losing months.

Family diagnostics:

- ETHUSDT Lorentzian `target_regime` is the strongest pre-May family, led by
  the top row above.
- Euclidean controls also produce loose rows, but none reaches annual-target
  stability.
- BTCUSDT positives are weaker and mostly concentrated in Euclidean
  cross-flow-regime controls.

May 2026 benchmark after fixed loose pre-May selection:

- May-positive selected rows: 35.
- May-negative selected rows: 48.
- May-flat selected rows: 17.
- Best May return: +0.013015.
- Worst May return: -0.062679.
- Median May return: 0.000000.

The top pre-May row benchmarks 7 May trades and +0.004604 net return, but its
pre-May annual loss profile already fails the target. The best May rows are
low-activity ETHUSDT path/session short variants with 2 May trades and
+0.013015 net return, not stable candidate-ready evidence.

## Decision

The causal Lorentzian regime KNN family is rejected as candidate-ready. The
packet gave the model a new feature set, causal frozen-neighbor accounting,
active 1-to-5/day signal targets, loss throttles, daily caps, and Euclidean
controls, but the best rows remain loss-clustered by month and no row meets
the annual stability target before May. May does not rescue the family because
the positive benchmark rows are either already unstable pre-May or too sparse
inside May.

Useful follow-up context: this result does not kill all KNN work, but it
rejects this completed-bar online regime-analog formulation. Any next KNN
packet needs a materially different label target, feature geometry, or
portfolio/ensemble construction rather than retuning only thresholds around
this score.

## Artifacts

- `data/research/wpr106_155_causal_lorentzian_regime_knn_search/wpr106_155_causal_lorentzian_regime_knn_summary.json`
- `data/research/wpr106_155_causal_lorentzian_regime_knn_search/pre_may/causal_lorentzian_regime_knn_ranking.parquet`
- `data/research/wpr106_155_causal_lorentzian_regime_knn_search/pre_may/causal_lorentzian_regime_knn_top2000.csv`
- `data/research/wpr106_155_causal_lorentzian_regime_knn_search/pre_may/causal_lorentzian_regime_knn_monthly_returns.parquet`
- `data/research/wpr106_155_causal_lorentzian_regime_knn_search/pre_may/family_summary.parquet`
- `data/research/wpr106_155_causal_lorentzian_regime_knn_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_155_causal_lorentzian_regime_knn_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_155_causal_lorentzian_regime_knn_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_155_causal_lorentzian_regime_knn_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_155_causal_lorentzian_regime_knn_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_155_causal_lorentzian_regime_knn_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_155_causal_lorentzian_regime_knn_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_155_causal_lorentzian_regime_knn_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_155_causal_lorentzian_regime_knn_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_155_causal_lorentzian_regime_knn_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
