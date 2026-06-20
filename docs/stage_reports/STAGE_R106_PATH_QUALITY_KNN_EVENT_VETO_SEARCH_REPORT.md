# Stage R106 Path-Quality KNN Event-Veto Search Report

Date: 2026-06-12
Work packet: WPR106-170-path-quality-knn-event-veto-search
Status: broad KNN variant completed, no candidate-ready lead

## Scope

WPR106-170 continues the 2024-forward broad search after WPR106-169 rejected
the completed-bar state and flow interaction screen. It gives the
Lorentzian/KNN family a materially different target: transparent completed-bar
event candidates are filtered by causal neighbors whose labels include future
net return and path quality, including adverse excursion.

All event thresholds, KNN features, label definitions, KNN parameters, filters,
ranking, and selection use 2024-01-01 through 2026-04-30 only. May 2026 is
replayed only after fixed pre-May rows are selected.

This packet is research-only and observe-only. It writes no candidate pack,
paper/live artifact, live configuration, sizing change, order path, CUDA
speedup claim, or promotion claim.

## Method

The runner uses the WPR106-96 verified BTCUSDT/ETHUSDT public-archive context
through May 2026:

- 15m completed bars;
- 1m aggTrade rows aggregated into completed 15m flow features.

It builds transparent signed event scores for:

- momentum continuation;
- pullback continuation;
- volatility-breakout continuation;
- range reversion;
- wick/flow absorption;
- cross-symbol relative strength.

It then precomputes KNN prediction caches for 18,179 BTCUSDT and 17,978
ETHUSDT query rows. The KNN geometry tests two feature packs:

- `path_quality`: target path, range, wick, volume, flow, and session features;
- `cross_event_flow`: target plus opposite-symbol path/flow and relative state.

Grid dimensions:

- symbols: BTCUSDT and ETHUSDT;
- event templates: six listed above;
- feature packs: two;
- fixed holds: 8, 16, and 32 bars;
- distances: Lorentzian and Euclidean;
- neighbors: 11 and 31;
- sessions: all, Asia, and US;
- target raw event rates: 1, 3, and 5 per active day;
- side modes: both, long-only, and short-only;
- path-good-rate filters: 0.50 and 0.55;
- minimum neighbor mean net filters: -0.0002 and 0.0;
- accepted-trade daily caps: 1, 3, and 5.

Neighbor labels are side-adjusted and require the neighbor label to be complete
before the query row. May 2026 neighbor pools are frozen to labels completed
before 2026-05-01. Costs are 0.0432% taker fee per side plus 0.0150%
slippage/spread per side, or 0.001164 round trip. Cost stress uses 1.0x,
1.25x, 1.5x, and 2.0x cost multipliers.

Compute used NumPy vectorized distance blocks and per-task prediction caches.
CUDA was not used and no speedup is claimed.

## Results

Full pre-May grid:

| Metric | Value |
| --- | ---: |
| Evaluated rows | 93,312 |
| Positive pre-May rows | 21,314 |
| Annual-target rows | 2,928 |
| Loose rows | 79 |
| Strict rows | 0 |
| Best pre-May net return | +1.001432 |
| Median pre-May net return | -0.096665 |

The fixed selected set contains only loose rows:

| Selected metric | Value |
| --- | ---: |
| Selected rows | 79 |
| Strict rows | 0 |
| Loose rows | 79 |
| Best pre-May net return | +0.895150 |
| Median pre-May net return | +0.211822 |
| Trade-count range | 61 to 280 |
| Active-month range | 22 to 28 |
| Losing-month range | 6 to 8 |
| Median trades per active day | 1.067797 |

The best selected row is:

- candidate: `pqknn-c82eae3c1c4828c5`;
- symbol: ETHUSDT;
- template: momentum continuation;
- feature pack: `cross_event_flow`;
- distance: Lorentzian;
- hold: 32 bars;
- neighbors: 11;
- session: all;
- side mode: short-only;
- target raw signals per day: 5;
- daily cap: 1;
- pre-May trades: 135;
- active months: 27;
- losing months: 7;
- annual losses: 2024: 4, 2025: 2, 2026 Jan-Apr: 1;
- pre-May net return: +0.895150;
- max drawdown: -0.219490;
- best-month share: 0.146392;
- cost-stress survival: 4/4.

It is not strict because it misses the annual stability target, mainly from
four losing months in 2024.

Selected group concentration:

| Segment | Selected rows |
| --- | ---: |
| BTCUSDT volatility-breakout continuation / cross-event-flow / Lorentzian | 12 |
| ETHUSDT volatility-breakout continuation / cross-event-flow / Lorentzian | 10 |
| BTCUSDT wick-flow absorption / cross-event-flow / Euclidean | 9 |
| ETHUSDT cross-symbol relative strength / path-quality / Euclidean | 8 |
| BTCUSDT volatility-breakout continuation / path-quality / Lorentzian | 6 |
| ETHUSDT pullback continuation / cross-event-flow / Lorentzian | 6 |
| ETHUSDT momentum continuation / cross-event-flow / Lorentzian | 6 |

## May Benchmark

May 2026 was benchmark-only after fixed pre-May selection:

| Metric | Value |
| --- | ---: |
| Selected rows benchmarked | 79 |
| May-positive rows | 0 |
| May-negative rows | 25 |
| May-flat rows | 54 |
| Best May return | +0.000000 |
| Worst May return | -0.016655 |
| Median May return | +0.000000 |
| May rows with positive cost-stress survival | 0 |

The 54 flat rows are not confirmation; they had no May trades after the fixed
pre-May filter. The 25 active May rows were all negative. The least negative
active May rows were BTCUSDT volatility-breakout variants with one May trade
and -0.000611 net return. The worst active rows were BTCUSDT
volatility-breakout variants with one May trade and -0.016655 net return.

## Decision

WPR106-170 rejects the path-quality KNN event-veto formulation as
candidate-ready, portfolio-ready, or promotion-ready evidence. The altered KNN
label target and path-quality veto produced loose pre-May pockets, but zero
strict rows and zero May-positive fixed selected rows make the result a clear
rejection.

Useful negative evidence: path-quality neighbor labels can improve aggregate
pre-May behavior for some transparent event families, especially ETH momentum
and BTC/ETH volatility-breakout variants, but the improvement is still
month-clustered and does not transfer to May 2026.

## Artifacts

- Runner:
  `data/research/wpr106_170_path_quality_knn_event_veto_search/scripts/run_wpr106_170_path_quality_knn_event_veto_search.py`
- Summary:
  `data/research/wpr106_170_path_quality_knn_event_veto_search/wpr106_170_path_quality_knn_event_veto_summary.json`
- Ranking:
  `data/research/wpr106_170_path_quality_knn_event_veto_search/pre_may/path_quality_knn_event_veto_ranking.parquet`
- Top 2000:
  `data/research/wpr106_170_path_quality_knn_event_veto_search/pre_may/path_quality_knn_event_veto_top2000.csv`
- Monthly returns:
  `data/research/wpr106_170_path_quality_knn_event_veto_search/pre_may/path_quality_knn_event_veto_monthly_returns.parquet`
- Selected rows and trades:
  `data/research/wpr106_170_path_quality_knn_event_veto_search/pre_may/selected_pre_may.parquet`
  and
  `data/research/wpr106_170_path_quality_knn_event_veto_search/pre_may/selected_pre_may_trades.parquet`
- May benchmark metrics and trades:
  `data/research/wpr106_170_path_quality_knn_event_veto_search/may_benchmark/selected_may_benchmark_metrics.parquet`
  and
  `data/research/wpr106_170_path_quality_knn_event_veto_search/may_benchmark/selected_may_benchmark_trades.parquet`
- Family summary:
  `data/research/wpr106_170_path_quality_knn_event_veto_search/pre_may/family_summary.parquet`

## Validation

Passed:

- `python -m compileall -q data\research\wpr106_170_path_quality_knn_event_veto_search\scripts`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`

Contract result: 460 passed.
