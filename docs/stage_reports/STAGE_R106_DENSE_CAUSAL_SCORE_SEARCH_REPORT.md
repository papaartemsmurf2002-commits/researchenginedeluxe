# Stage R106 Dense Causal Score Search Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-106-dense-causal-score-search.md`
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It uses
2024-01-01 through 2026-04-30 for optimization, score-threshold calibration,
ranking, filtering, and selection. May 2026 is excluded from feature choice,
score choice, threshold calibration, hold choice, ranking, and selection. May
2026 is joined only after pre-May loose/strict rows are selected, and only as a
benchmark holdout. No candidate pack, paper/live artifact, order placement,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim is made.

## Method

The artifact runner uses the WPR106-96 verified BTCUSDT/ETHUSDT public-archive
context from 2024-01-01 through 2026-05-31. Both symbols have 84,672 15m bars
and matching aggTrade flow context. Signals are generated from completed 15m
bars and enter on the next bar. Pre-May trades must exit before 2026-05-01.

The runner builds cached causal 15m feature arrays per symbol, including return
z-scores, channel location, wick balance, close location, range/ATR state,
quote-volume state, time-of-day/day-of-week terms, and 15m aggTrade quote-flow
imbalance. It then evaluates deterministic transparent score templates across
momentum, flow-follow, flow-fade, wick-fade, range-fade, compression-breakout,
volatility-breakout, session-drift, calendar-flow, micro-reversal, and balanced
price/flow families.

All score thresholds are quantiles calibrated only on eligible pre-May rows for
the candidate's symbol, template, side mode, hold, session, day mode, volatility
filter, and target signal density. The same fixed threshold is later applied to
May only for selected pre-May rows. Candidates use one-position-at-a-time
overlap handling and explicit round-trip cost of 0.0432% taker fee per side
plus 0.0150% slippage/spread allowance per side. The search runs BTCUSDT and
ETHUSDT in separate worker processes and uses vectorized/cached feature arrays;
no CUDA path is used or claimed.

## Results

The screen evaluated 129,600 dense score rows: 64,800 per symbol. It found
6,656 positive pre-May rows and 369 loose pre-May rows, but zero strict
month-stability rows.

| Scope | Rows | Positive Pre-May | Loose Rows | Strict Rows | Best Pre-May Return |
| --- | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | 64,800 | 1,307 | 59 | 0 | +0.617279 |
| ETHUSDT | 64,800 | 5,349 | 310 | 0 | +1.221821 |
| Total | 129,600 | 6,656 | 369 | 0 | +1.221821 |

The active-rate hypothesis was not the blocker: all 6,656 positive rows landed
inside the 1-to-5 trades per active day band after overlap handling, 6,619
positive rows were active in at least 24 pre-May months, and 2,947 positive rows
had cost-stress survival of at least 0.75. The blocker is the annual stability
target. Among all 6,656 positive rows, zero met the full-year constraint of two
or fewer losing active months in both 2024 and 2025; zero also met the combined
full-year plus partial-2026 target.

Top selected pre-May rows:

| Rank | Candidate | Family | Pre-May Return | Trades | Trades/Active Day | Active Months | Losing Months | Annual Losses | May Return | May Trades | Note |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |
| 1 | `dense-dd0fd73ff84d042a` | ETHUSDT volatility breakout | +1.006293 | 321 | 1.000 | 28 | 10 | 2024: 4, 2025: 5, 2026 Jan-Apr: 1 | -0.012451 | 7 | High return, annual target fail, May negative. |
| 2 | `dense-1d75e0327d994001` | ETHUSDT balanced | +0.909662 | 316 | 1.129 | 28 | 10 | 2024: 3, 2025: 6, 2026 Jan-Apr: 1 | -0.104549 | 10 | Annual target fail, May strongly negative. |
| 3 | `dense-c97cbc47d75d2c94` | ETHUSDT session drift | +0.872790 | 573 | 1.411 | 28 | 9 | 2024: 5, 2025: 3, 2026 Jan-Apr: 1 | -0.061804 | 18 | Annual target fail, May negative. |
| 4 | `dense-d54c43082932f4c3` | ETHUSDT momentum | +0.870015 | 217 | 1.000 | 28 | 10 | 2024: 5, 2025: 4, 2026 Jan-Apr: 1 | -0.042307 | 7 | Annual target fail, May negative. |
| 5 | `dense-1308bf874e851fb9` | ETHUSDT volatility breakout | +0.855667 | 328 | 1.000 | 28 | 9 | 2024: 3, 2025: 5, 2026 Jan-Apr: 1 | -0.040762 | 8 | Annual target fail, May negative. |

All 369 loose pre-May rows were benchmarked in May after selection. May results:

| Selected Set | Rows | May Positive | May Negative | May Flat | May Trades |
| --- | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT loose rows | 59 | 10 | 49 | 0 | included in total |
| ETHUSDT loose rows | 310 | 97 | 212 | 1 | included in total |
| Total loose rows | 369 | 107 | 261 | 1 | 2,596 |

The best May-positive diagnostics do not rescue the family because they were
already rejected by pre-May annual stability. For example:

| Candidate | Pre-May Return | Pre-May Losing Months | Annual Losses | May Return | May Trades | Note |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| `dense-945c44cb56b0acb7` | +0.459584 | 10 | 2024: 6, 2025: 1, 2026 Jan-Apr: 3 | +0.087851 | 20 | Best May row, fails annual target. |
| `dense-788f0c14f98eaab4` | +0.267152 | 10 | 2024: 3, 2025: 4, 2026 Jan-Apr: 3 | +0.046554 | 22 | May positive, pre-May unstable. |
| `dense-304e5c90f9b93cc9` | +0.341134 | 10 | 2024: 6, 2025: 3, 2026 Jan-Apr: 1 | +0.034476 | 9 | May positive, pre-May unstable. |
| `dense-46cc7b3cebf4f533` | +0.763425 | 8 | 2024: 3, 2025: 3, 2026 Jan-Apr: 2 | +0.032414 | 12 | Stronger pre-May, still annual target fail. |

Closest annual-stability diagnostics still miss the target. The best cluster by
loss count is an ETHUSDT volatility-breakout compression row around
`dense-5c5171e10ca93a1a`: +0.449586 pre-May, 182 trades, 28 active months,
6 losing months, and 1.052 trades per active day, but it loses 4 months in
2024 and 2 months in 2026 Jan-Apr. It is not a strict lead.

## Interpretation

WPR106-106 materially expands the broad search away from the rejected sparse
side-veto and sleeve-defense path. Dense transparent score entries can create
active, cost-positive pre-May rows, especially on ETHUSDT, and the active-rate
goal is feasible after overlap handling. The key requested target remains
unmet: none of the positive rows reaches month-to-month stability close to
zero-to-two losing months per full year. May benchmarking is mixed but mostly
negative across selected loose rows, and May-positive rows are pre-May rejected
before the holdout is considered.

The dense causal score family is therefore rejected as currently configured.
It is useful diagnostic evidence that the search can support 1-to-5 trades/day
without immediate cost failure, but it does not produce a candidate-ready or
promotion-ready lead.

## Artifacts

- `data/research/wpr106_106_dense_causal_score_search/scripts/run_wpr106_106_dense_score_search.py`
- `data/research/wpr106_106_dense_causal_score_search/wpr106_106_dense_score_summary.json`
- `data/research/wpr106_106_dense_causal_score_search/wpr106_106_runner.log`
- `data/research/wpr106_106_dense_causal_score_search/wpr106_106_selected_all_loose_refresh.log`
- `data/research/wpr106_106_dense_causal_score_search/pre_may/combined_ranking.parquet`
- `data/research/wpr106_106_dense_causal_score_search/pre_may/combined_ranking.csv`
- `data/research/wpr106_106_dense_causal_score_search/pre_may/family_summary.parquet`
- `data/research/wpr106_106_dense_causal_score_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_106_dense_causal_score_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_106_dense_causal_score_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_106_dense_causal_score_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_106_dense_causal_score_search/scripts`: passed.
- `python -m compileall -q src/tradingbotsuite`: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`: 460 passed.
