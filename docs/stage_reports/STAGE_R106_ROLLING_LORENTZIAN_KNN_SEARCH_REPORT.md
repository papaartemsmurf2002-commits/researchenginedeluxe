# Stage R106 Rolling Lorentzian KNN Search Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-107-rolling-lorentzian-knn-search.md`
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It uses
2024-01-01 through 2026-04-30 for feature-pack choice, KNN parameter choice,
score-threshold calibration, ranking, filtering, and selection. May 2026 is
excluded from all tuning and selection. May is joined only after pre-May
loose/strict rows are selected, and only as a benchmark holdout. No candidate
pack, paper/live artifact, order placement, sizing change, runtime-mode change,
live configuration write, CUDA speedup claim, or promotion claim is made.

## Method

The artifact runner uses the WPR106-96 verified BTCUSDT/ETHUSDT public-archive
context from 2024-01-01 through 2026-05-31. Both symbols have 84,672 15m bars
and matching 1m aggTrade flow context. The runner computes point-in-time
completed-bar features and evaluates signals on 1-hour grid points, entering on
the next 15m open and enforcing one open position per candidate.

This is a scoped artifact-only KNN implementation rather than a rerun of prior
no-RSI matrix settings. It tests rolling causal neighbor pools where neighbors
must be older than the signal by at least the label horizon plus purge gap. For
May benchmark rows, neighbor labels are frozen to labels that completed before
2026-05-01, so the holdout does not self-train as May progresses.

Feature packs:

- `micro_path_flow`: short return path, bar range, wick balance, channel
  location, and aggTrade quote-flow imbalance;
- `trend_session_flow`: slower return/channel state, session phase, and slow
  flow;
- `reversal_wick_range`: local reversal, candle close location, wick balance,
  channel location, and range state;
- `compression_flow`: range compression, return pressure, quote volume, flow,
  channel location, and ATR state.

The search compares Lorentzian and Euclidean distances across 960/2,880-bar
lookbacks, 15/31 neighbors, 8/16/32-bar labels, 8/16-bar train spacing,
long/short/both side modes, sessions, volatility/flow filters, and pre-May-only
quantile thresholds for 1, 2, 3, or 5 target signals per active day. Costs are
0.0432% taker fee per side plus 0.0150% slippage/spread allowance per side.
The run used two worker processes. No CUDA path was used or claimed.

## Results

The screen evaluated 73,728 KNN rows: 36,864 per symbol. It found 1,270
positive pre-May rows, 27 loose pre-May rows, and zero strict month-stability
rows.

| Scope | Rows | Positive Pre-May | Loose Rows | Strict Rows | Best Pre-May Return |
| --- | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | 36,864 | 192 | 0 | 0 | +0.407503 |
| ETHUSDT | 36,864 | 1,078 | 27 | 0 | +0.829823 |
| Total | 73,728 | 1,270 | 27 | 0 | +0.829823 |

Active-rate behavior was not the main blocker. All 1,270 positive rows landed
inside 1 to 5 trades per active day, and 1,269 positive rows were active in at
least 24 pre-May months. Cost survival was weaker: 212 positive rows survived
at least 0.75 of cost-stress scenarios. The decisive blocker was annual
stability: zero positive rows met the full-year constraint of two or fewer
losing active months in both 2024 and 2025, and zero met the combined full-year
plus partial-2026 target.

Top selected pre-May rows:

| Rank | Candidate | Feature Pack | Metric | Pre-May Return | Trades | Trades/Active Day | Active Months | Losing Months | Annual Losses | May Return | May Trades | Note |
| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |
| 1 | `rknn-59968119d9c264fb` | reversal_wick_range | Lorentzian | +0.829823 | 461 | 1.000 | 27 | 8 | 2024: 2, 2025: 4, 2026 Jan-Apr: 2 | -0.026627 | 15 | Best row; annual target fail; May negative. |
| 2 | `rknn-57a7411f5e8140f9` | compression_flow | Euclidean | +0.707222 | 641 | 1.000 | 27 | 9 | 2024: 4, 2025: 4, 2026 Jan-Apr: 1 | -0.035298 | 25 | Annual target fail; May negative. |
| 3 | `rknn-cb8f278b5a074a98` | compression_flow | Lorentzian | +0.695524 | 730 | 1.000 | 27 | 10 | 2024: 5, 2025: 3, 2026 Jan-Apr: 2 | -0.009392 | 29 | Annual target fail; May negative. |
| 5 | `rknn-8f2e4eaf5b812e3a` | compression_flow | Lorentzian | +0.591456 | 894 | 1.298 | 27 | 8 | 2024: 3, 2025: 2, 2026 Jan-Apr: 3 | -0.078920 | 25 | Meets 2025 only; 2026 and May reject. |
| 7 | `rknn-6aef6a878f51686b` | reversal_wick_range | Euclidean | +0.534865 | 445 | 1.000 | 27 | 10 | 2024: 4, 2025: 4, 2026 Jan-Apr: 2 | +0.030383 | 18 | May-positive, but pre-May annual target fail. |

All 27 loose pre-May rows were benchmarked in May after selection. May results:

| Selected Set | Rows | May Positive | May Negative | May Flat |
| --- | ---: | ---: | ---: | ---: |
| ETHUSDT loose rows | 27 | 4 | 21 | 2 |

The best May-positive rows were already rejected by pre-May annual stability:

| Candidate | Pre-May Return | Pre-May Losing Months | Annual Losses | May Return | May Trades | Note |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| `rknn-6aef6a878f51686b` | +0.534865 | 10 | 2024: 4, 2025: 4, 2026 Jan-Apr: 2 | +0.030383 | 18 | May positive, pre-May unstable. |
| `rknn-f97eb79f6555c50e` | +0.392052 | 10 | 2024: 5, 2025: 3, 2026 Jan-Apr: 2 | +0.024269 | 8 | May positive, pre-May unstable. |
| `rknn-18ae4f2b88e91790` | +0.378498 | 10 | 2024: 3, 2025: 4, 2026 Jan-Apr: 3 | +0.020363 | 24 | May positive, pre-May unstable. |

Feature/metric summary:

| Symbol | Feature Pack | Metric | Rows | Positive Rows | Loose Rows | Best Return | Fewest Losing Months |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | trend_session_flow | Euclidean | 4,608 | 16 | 0 | +0.407503 | 12 |
| BTCUSDT | micro_path_flow | Euclidean | 4,608 | 33 | 0 | +0.363648 | 10 |
| BTCUSDT | compression_flow | Euclidean | 4,608 | 45 | 0 | +0.316847 | 11 |
| BTCUSDT | reversal_wick_range | Euclidean | 4,608 | 27 | 0 | +0.275909 | 9 |
| ETHUSDT | reversal_wick_range | Lorentzian | 4,608 | 139 | 3 | +0.829823 | 8 |
| ETHUSDT | compression_flow | Euclidean | 4,608 | 208 | 3 | +0.820157 | 9 |
| ETHUSDT | compression_flow | Lorentzian | 4,608 | 169 | 8 | +0.714597 | 8 |
| ETHUSDT | trend_session_flow | Euclidean | 4,608 | 81 | 3 | +0.581160 | 10 |

## Interpretation

WPR106-107 gives the Lorentzian/KNN family a materially different test: rolling
causal neighbor pools, explicit purge, feature packs not limited to the prior
no-RSI mapping, threshold calibration on pre-May only, and May scoring with
pre-May neighbor labels frozen. It finds real positive pockets on ETHUSDT, and
the top Lorentzian row is a credible diagnostic improvement over prior sparse
KNN rows in activity and aggregate return.

The family still fails the requested target. No positive KNN row satisfies the
full-year annual stability rule, no strict row exists, and the selected loose
rows are mostly rejected by May. The few May-positive rows were already rejected
before May by pre-May annual stability. This is therefore negative diagnostic
evidence, not a candidate-ready lead.

## Artifacts

- `data/research/wpr106_107_rolling_lorentzian_knn_search/scripts/run_wpr106_107_rolling_knn_search.py`
- `data/research/wpr106_107_rolling_lorentzian_knn_search/wpr106_107_rolling_knn_summary.json`
- `data/research/wpr106_107_rolling_lorentzian_knn_search/wpr106_107_runner.log`
- `data/research/wpr106_107_rolling_lorentzian_knn_search/pre_may/combined_ranking.parquet`
- `data/research/wpr106_107_rolling_lorentzian_knn_search/pre_may/combined_ranking.csv`
- `data/research/wpr106_107_rolling_lorentzian_knn_search/pre_may/feature_metric_summary.parquet`
- `data/research/wpr106_107_rolling_lorentzian_knn_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_107_rolling_lorentzian_knn_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_107_rolling_lorentzian_knn_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_107_rolling_lorentzian_knn_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_107_rolling_lorentzian_knn_search/scripts`: passed.
- `python -m compileall -q src/tradingbotsuite`: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`: 460 passed.
