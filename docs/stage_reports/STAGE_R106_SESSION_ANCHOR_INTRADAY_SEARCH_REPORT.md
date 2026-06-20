# Stage R106 Session Anchor Intraday Search Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-109-session-anchor-intraday-search.md`
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It uses
2024-01-01 through 2026-04-30 for family choice, anchor-window choice,
score-threshold calibration, hold choice, session/filter choice, ranking, and
selection. May 2026 is excluded from all tuning and selection. May is joined
only after pre-May loose/strict rows are selected, and only as a benchmark
holdout. No candidate pack, paper/live artifact, order placement, sizing
change, runtime-mode change, live configuration write, CUDA speedup claim, or
promotion claim is made.

## Method

The artifact runner uses the WPR106-96 verified BTCUSDT/ETHUSDT public-archive
context from 2024-01-01 through 2026-05-31. Both symbols contribute 84,672
completed 15m rows. Matching 1m aggTrade files are aggregated to 15m
quote-flow imbalance and merged into the bar context.

Signals use completed 15m bars and enter on the next 15m open. Pre-May trades
must exit before 2026-05-01. One-position overlap handling is enforced before
active-rate metrics are measured. Costs are 0.0432% taker fee per side plus a
0.0150% slippage/spread allowance per side.

The screen tests daily and session anchors:

- daily opening-range breakout and fade using 4/8/16 completed 15m bars;
- prior-day high/low breakout and fade;
- Asia range breakout and fade after the 00:00-08:00 UTC range is known;
- Europe opening-range breakout and fade after the 07:00-09:00 UTC range is
  known;
- daily VWAP momentum and fade;
- session-transition momentum and reversal.

The grid covers BTCUSDT and ETHUSDT, 4/8/16/32/64-bar holds, all/Asia/Europe/US
sessions, all/calm/wide/flow-active filters, and pre-May-only quantile
thresholds targeting 1, 2, 3, or 5 signals per day.

## Results

The screen evaluated 9,600 rows. It found 1,436 positive pre-May rows, 150
loose pre-May rows, and zero strict month-stability rows.

| Scope | Rows |
| --- | ---: |
| Evaluated rows | 9,600 |
| Positive pre-May rows | 1,436 |
| Loose pre-May rows | 150 |
| Strict pre-May rows | 0 |
| Selected May benchmark rows | 150 |
| May-positive selected rows | 19 |
| May-negative selected rows | 118 |
| May-flat selected rows | 13 |

The active-rate hypothesis was not the blocker. All 1,436 positive rows landed
inside 1 to 5 trades per active day after overlap handling; 1,428 positive rows
were active in at least 24 months, and 887 had cost-stress survival of at least
0.75. The blocker was month-to-month stability: zero positive rows met the
full-year target of two or fewer losing active months in both 2024 and 2025,
and zero met the combined full-year plus partial-2026 target.

Family-level pre-May summary:

| Symbol | Family / Template | Rows | Positive | Loose | Best Return | Best Losing Months |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | prior-day range breakout | 320 | 53 | 5 | +0.667656 | 8 |
| BTCUSDT | opening-range breakout | 960 | 157 | 7 | +0.487733 | 7 |
| BTCUSDT | VWAP momentum | 320 | 31 | 3 | +0.465822 | 9 |
| BTCUSDT | Asia/Europe range breakouts | 480 | 101 | 6 | +0.449437 | 8 |
| ETHUSDT | session-transition momentum | 320 | 74 | 2 | +1.617296 | 8 |
| ETHUSDT | prior-day range breakout | 320 | 132 | 33 | +1.405336 | 6 |
| ETHUSDT | VWAP momentum | 320 | 127 | 5 | +1.339231 | 7 |
| ETHUSDT | opening-range breakout | 960 | 458 | 63 | +1.200645 | 7 |
| ETHUSDT | Asia/Europe range breakouts | 480 | 253 | 26 | +0.967880 | 7 |

Fade/reversal variants were not competitive. The best BTC fade row returned
+0.214759 with 12 losing months, and the best ETH fade/reversal row returned
+0.478405 with 11 losing months. VWAP fades and Europe/Asia range fades were
negative at the family-best level for at least one symbol.

Top selected rows by pre-May return:

| Rank | Candidate | Family | Pre-May Return | Trades | Trades/Active Day | Active Months | Annual Losses | May Return | May Trades | Note |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |
| 1 | `anchor-6719209fb0b21325` | ETH prior-day breakout | +1.405336 | 193 | 1.078 | 28 | 2024: 3, 2025: 3, 2026 Jan-Apr: 1 | -0.017786 | 6 | High return, annual target fail, May negative. |
| 2 | `anchor-21f7fd970880b552` | ETH prior-day breakout | +1.242248 | 197 | 1.082 | 28 | 2024: 3, 2025: 3, 2026 Jan-Apr: 1 | -0.012663 | 6 | Same instability shape, May negative. |
| 3 | `anchor-2503a444844a78c8` | ETH prior-day breakout | +1.196315 | 207 | 1.067 | 28 | 2024: 2, 2025: 4, 2026 Jan-Apr: 1 | -0.012682 | 6 | Fails 2025 annual cap, May negative. |
| 7 | `anchor-226d909f37eec987` | ETH VWAP momentum | +1.079975 | 290 | 1.021 | 28 | 2024: 3, 2025: 4, 2026 Jan-Apr: 1 | -0.003977 | 10 | High drawdown and annual target fail. |
| 8 | `anchor-ed8326c3303ab76b` | ETH opening-range breakout | +1.077828 | 203 | 1.253 | 28 | 2024: 2, 2025: 4, 2026 Jan-Apr: 2 | -0.019362 | 4 | Annual target fail, May negative. |

The closest stability row was still not strict:

| Candidate | Family | Pre-May Return | Trades | Active Months | Losing Months | Annual Losses | May Return | May Trades | Note |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |
| `anchor-e56191d930311a7f` | ETH prior-day breakout | +0.916244 | 259 | 28 | 6 | 2024: 2, 2025: 3, 2026 Jan-Apr: 1 | +0.009101 | 7 | Best stability among selected rows, but misses 2025 by one losing month. |

May benchmark behavior was weak overall. Only 19 of 150 fixed selected rows were
May-positive; 118 were May-negative and 13 were flat. The two best BTC May rows
were prior-day breakout variants, `anchor-9e68fb4657e64465` at +0.018723 and
`anchor-125c3cb4afa2cd09` at +0.018200, but both had 10 pre-May losing months
and failed annual stability before May was checked. The best ETH May row,
`anchor-2b35bf9adf802ede`, returned +0.015372 on one May trade but had nine
pre-May losing months and a 2025 loss count of five.

## Interpretation

WPR106-109 adds a materially different family to the broad 2024-forward search.
Session and daily anchor breakouts can produce active and cost-positive
pre-May rows, especially on ETHUSDT prior-day and opening-range breakout
variants. They do not satisfy the requested month-to-month stability profile.

This family is therefore diagnostic rather than candidate-ready. It supports
continuing to allow 1 to 5 trades per active day, because active-rate density
was feasible after overlap handling and costs. It does not support promoting a
session-anchor lead: strict rows are absent, every positive row fails the
full-year annual stability target, and the May benchmark mostly contradicts the
loose pre-May selections.

## Artifacts

- `data/research/wpr106_109_session_anchor_intraday_search/scripts/run_wpr106_109_session_anchor_search.py`
- `data/research/wpr106_109_session_anchor_intraday_search/wpr106_109_session_anchor_summary.json`
- `data/research/wpr106_109_session_anchor_intraday_search/wpr106_109_runner.log`
- `data/research/wpr106_109_session_anchor_intraday_search/pre_may/combined_ranking.parquet`
- `data/research/wpr106_109_session_anchor_intraday_search/pre_may/combined_ranking.csv`
- `data/research/wpr106_109_session_anchor_intraday_search/pre_may/family_summary.parquet`
- `data/research/wpr106_109_session_anchor_intraday_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_109_session_anchor_intraday_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_109_session_anchor_intraday_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_109_session_anchor_intraday_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_109_session_anchor_intraday_search/scripts`: passed.
- `python -m compileall -q src/tradingbotsuite`: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`: 460 passed.
