# Stage R106 Broad Bar-State Flow Interaction Screen Report

Date: 2026-06-12
Work packet: WPR106-169-broad-bar-state-flow-interaction-screen
Status: broad screen completed, no candidate-ready lead

## Scope

WPR106-169 returned to broad 2024-forward research after WPR106-168 rejected
the WPR146 threshold-5 descriptor on a fresh June holdout. This packet tested
completed 15m bar-state, aggTrade-flow proxy, and cross-symbol interaction
scores for BTCUSDT and ETHUSDT.

All scoring, feature choices, thresholds, filters, holds, ranking, and
selection used 2024-01-01 through 2026-04-30 only. May 2026 was replayed only
after fixed pre-May rows were selected.

The packet is research-only and observe-only. It writes no candidate pack, no
paper/live artifact, no live configuration, no sizing change, no order path,
and no promotion claim.

## Method

The runner used the WPR106-96 source context:

- BTCUSDT/ETHUSDT 15m bars from 2024-01-01 through 2026-05-31;
- BTCUSDT/ETHUSDT 1m aggTrade-flow proxy aggregated into completed 15m bars.

It built vectorized feature caches for 96, 384, and 1536-bar normalization
windows, then searched:

- symbols: BTCUSDT and ETHUSDT;
- templates: momentum continuation, pullback continuation, range reversion,
  wick/flow absorption, volatility-breakout continuation, volatility-breakout
  fade, cross-symbol relative strength, and cross-symbol catch-up reversion;
- holds: 8, 16, 32, and 64 bars;
- sessions: all, Asia, EU, and US;
- volatility gates: all, high-range, and compressed-prior;
- flow gates: all, flow-confirm, flow-contra, and flow-neutral;
- side modes: both, long-only, and short-only;
- target raw signal rates: 1, 3, and 5 per active day;
- accepted-trade daily caps: 1, 3, and 5.

Every candidate used next-bar entry, fixed-hold exit, one-position-at-a-time
overlap handling, daily caps, and the established round-trip cost of 0.001164.
Cost stress used 1.0x, 1.25x, 1.5x, and 2.0x costs.

## Results

Full pre-May grid:

| Metric | Value |
| --- | ---: |
| Evaluated rows | 248,832 |
| Positive pre-May rows | 40,753 |
| Annual-target rows | 2,042 |
| Loose rows | 384 |
| Strict rows | 0 |
| Best pre-May net return | +1.979664 |
| Median pre-May net return | -0.304863 |

The selected top 100 rows were all loose and pre-May positive, but none were
strict:

| Selected metric | Value |
| --- | ---: |
| Selected rows | 100 |
| Median pre-May net return | +0.952125 |
| Best pre-May net return | +1.979664 |
| Trade count range | 79 to 485 |
| Active month range | 25 to 28 |
| Losing month range | 4 to 8 |
| Cost-stress survival | 100/100 at 4/4 |
| Median trades per active day | 1.000000 |

Selected rows were heavily concentrated in ETHUSDT:

| Segment | Selected rows |
| --- | ---: |
| ETHUSDT momentum continuation | 45 |
| ETHUSDT volatility-breakout continuation | 26 |
| ETHUSDT pullback continuation | 15 |
| ETHUSDT cross-symbol relative strength | 10 |
| BTCUSDT volatility-breakout continuation | 2 |
| BTCUSDT momentum continuation | 2 |

May 2026 benchmark after fixed pre-May selection:

| Metric | Value |
| --- | ---: |
| May-positive rows | 31 |
| May-negative rows | 69 |
| May-flat rows | 0 |
| Best May return | +0.048723 |
| Worst May return | -0.177795 |
| Median May return | -0.042965 |
| Rows with positive May cost-stress survival | 31 |

## Follow-Up Clue

The strongest fixed May-positive clue was:

- symbol: ETHUSDT;
- family/template: volatility-breakout continuation;
- session: Asia;
- flow filter: flow-contra;
- volatility filter: all;
- side mode: both;
- hold: 64 bars;
- normalization window: 1536 bars;
- target raw signals per day: 3;
- accepted daily caps: 1, 3, or 5 produced the same May path.

That row recorded:

| Metric | Value |
| --- | ---: |
| Pre-May net return | +0.811320 |
| Pre-May trades | 205 |
| Pre-May active months | 27 |
| Pre-May losing months | 7 |
| Annual losses | 3/3/1 |
| Pre-May max drawdown | -0.265408 |
| Pre-May best-month share | 0.121200 |
| Pre-May cost-stress survival | 1.000000 |
| May trades | 7 |
| May net return | +0.048723 |
| May max drawdown | -0.006872 |
| May cost-stress survival | 1.000000 |

This is not a candidate. It misses the requested annual stability target and
fails strict pre-May gates. It is only a research-only clue for a later
pre-May-only causal repair, such as stricter regime state, better non-calendar
drawdown control, or a dedicated exit model.

## Decision

WPR106-169 rejects the broad bar-state/flow interaction screen as
candidate-ready, portfolio-ready, or promotion-ready evidence. The broad screen
did find many positive pre-May rows and some May-positive rows, but zero strict
pre-May rows and a negative selected-set May median show that this family, as
configured, is not stable enough.

No candidate pack, paper/live artifact, order path, sizing change, runtime-mode
change, live config write, CUDA speedup claim, or promotion claim exists.

## Artifacts

- Runner:
  `data/research/wpr106_169_broad_bar_state_flow_interaction_screen/scripts/run_wpr106_169_broad_bar_state_flow_interaction_screen.py`
- Summary:
  `data/research/wpr106_169_broad_bar_state_flow_interaction_screen/wpr106_169_broad_bar_state_flow_interaction_screen_summary.json`
- Ranking:
  `data/research/wpr106_169_broad_bar_state_flow_interaction_screen/pre_may/bar_state_flow_ranking.parquet`
- Top 2000:
  `data/research/wpr106_169_broad_bar_state_flow_interaction_screen/pre_may/bar_state_flow_top2000.csv`
- Monthly returns:
  `data/research/wpr106_169_broad_bar_state_flow_interaction_screen/pre_may/bar_state_flow_monthly_returns.parquet`
- Selected rows:
  `data/research/wpr106_169_broad_bar_state_flow_interaction_screen/pre_may/selected_pre_may.parquet`
- Selected pre-May trades:
  `data/research/wpr106_169_broad_bar_state_flow_interaction_screen/pre_may/selected_pre_may_trades.parquet`
- May benchmark metrics/trades:
  `data/research/wpr106_169_broad_bar_state_flow_interaction_screen/may_benchmark/selected_may_benchmark_metrics.parquet`
  and
  `data/research/wpr106_169_broad_bar_state_flow_interaction_screen/may_benchmark/selected_may_benchmark_trades.parquet`
- Family summary:
  `data/research/wpr106_169_broad_bar_state_flow_interaction_screen/pre_may/family_summary.parquet`

## Validation

Passed:

- `python -m compileall -q data/research/wpr106_169_broad_bar_state_flow_interaction_screen/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

Contract result: 460 passed.
