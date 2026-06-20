# Stage R106 Anti-Signal Entry/Exit Screen Report

Date: 2026-06-12
Work packet: WPR106-173-anti-signal-entry-exit-screen
Status: anti-signal screen completed, strict pre-May rows rejected by May

## Scope

WPR106-173 continues the 2024-forward broad search after WPR106-172 rejected
the adaptive barrier entry/exit screen. It tests a materially different
directional hypothesis: transparent completed-bar strategy scores may be more
useful as explicit opposite-side anti-signals than as direct signals.

All feature definitions, thresholds, regime filters, side policies, exits,
daily caps, ranking, and selection use only 2024-01-01 through 2026-04-30. May
2026 is replayed only after fixed pre-May rows are selected.

This packet is research-only and observe-only. It writes no candidate pack,
paper/live artifact, live configuration, sizing change, order path, CUDA
speedup claim, or promotion claim.

## Method

Inputs:

- WPR106-96 BTCUSDT/ETHUSDT 15m bars from 2024-01-01 through 2026-05-31;
- WPR106-96 BTCUSDT/ETHUSDT 1m aggTrade rows aggregated into completed 15m
  flow-pressure features.

The runner reuses the WPR106-172 transparent completed-bar score definitions
but makes side policy explicit:

- `side_policy: inverse_signal`;
- a positive source score is traded short;
- a negative source score is traded long;
- `long` and `short` side modes refer to actual anti-signal trade side, not the
  original score sign.

Entry templates:

- `trend_pullback_follow`;
- `range_reversion_fade`;
- `vol_breakout_follow`;
- `wick_sweep_reversal`;
- `flow_price_divergence_fade`;
- `flow_burst_follow`;
- `compression_breakout_follow`.

Grid dimensions:

- symbols: BTCUSDT and ETHUSDT;
- normalization windows: 96 and 384 bars;
- sessions: all and US;
- regime filters: all, high-volatility, flow-confirm, flow-contra, and
  range-compression;
- side modes: both, long-only, and short-only, applied to actual anti-signal
  side;
- target raw signal rates: 1, 3, and 5 per active day;
- exits: fixed 16, 32, and 64 bars plus ATR barrier `h16 tp1/sl1` and
  `h32 tp2/sl1`;
- accepted-trade daily caps: 1, 3, and 5.

ATR barriers use the completed signal-bar ATR estimate. If a stop and target
are both reachable within the same bar, the stop is counted first. Costs are
0.0432% taker fee per side plus 0.0150% slippage/spread per side, or 0.001164
round trip. Cost stress uses 1.0x, 1.25x, 1.5x, and 2.0x cost multipliers.

The runner completed in 483.5 seconds. CUDA was not used and no speedup is
claimed.

## Results

Full pre-May grid:

| Metric | Value |
| --- | ---: |
| Evaluated rows | 35,550 |
| Positive pre-May rows | 4,618 |
| Annual-target rows | 166 |
| Loose rows | 209 |
| Strict rows | 14 |

The fixed selected set contains both strict and loose rows:

| Selected metric | Value |
| --- | ---: |
| Selected rows | 100 |
| Strict rows | 14 |
| Loose rows | 86 |
| Best pre-May net return | +1.899726 |
| Median pre-May net return | +0.894432 |
| Worst pre-May net return | +0.170107 |

All 14 strict rows are ETHUSDT `vol_breakout_follow` anti-signals with the
conservative `barrier_h32_tp2_sl1` exit. They differ by side mode, regime
filter, threshold, and daily cap.

The top strict row is:

- candidate: `adaptexit-cd665cb7c11c610a`;
- symbol: ETHUSDT;
- template: `vol_breakout_follow`;
- side mode: actual anti-signal long-only;
- regime filter: `high_vol`;
- exit: `barrier_h32_tp2_sl1`;
- daily cap: 5;
- pre-May trades: 871;
- trades per active day: 2.837134;
- active months: 28;
- losing months: 4;
- annual losses: 2024: 1, 2025: 2, 2026 Jan-Apr: 1;
- pre-May net return: +1.389897;
- max drawdown: -0.155732;
- best-month share: 0.115501;
- cost-stress survival: 4/4.

Template summary:

| Template | Positive rows | Annual-target rows | Loose rows | Strict rows | Median net | Best net |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `vol_breakout_follow` | 990 | 161 | 121 | 14 | -0.243713 | +1.899726 |
| `flow_burst_follow` | 404 | 0 | 39 | 0 | -0.374022 | +0.977914 |
| `range_reversion_fade` | 1,554 | 1 | 17 | 0 | -0.135150 | +0.844015 |
| `compression_breakout_follow` | 410 | 0 | 12 | 0 | -0.438664 | +1.572105 |
| `trend_pullback_follow` | 462 | 4 | 12 | 0 | -0.340827 | +0.753404 |
| `wick_sweep_reversal` | 588 | 0 | 8 | 0 | -0.470106 | +1.624792 |
| `flow_price_divergence_fade` | 210 | 0 | 0 | 0 | -0.455533 | +0.906041 |

Exit summary:

| Exit | Positive rows | Annual-target rows | Loose rows | Strict rows | Median net | Best net |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `barrier_h32_tp2_sl1` | 1,273 | 43 | 174 | 14 | -0.227259 | +1.899726 |
| `fixed_64` | 1,639 | 45 | 22 | 0 | -0.278051 | +1.624792 |
| `fixed_32` | 1,015 | 46 | 7 | 0 | -0.364741 | +0.906041 |
| `fixed_16` | 664 | 32 | 4 | 0 | -0.434491 | +0.778938 |
| `barrier_h16_tp1_sl1` | 27 | 0 | 2 | 0 | -0.452547 | +0.106732 |

## May Benchmark

May 2026 was benchmark-only after fixed pre-May selection:

| Metric | Value |
| --- | ---: |
| Selected rows benchmarked | 100 |
| May-positive rows | 10 |
| May-negative rows | 42 |
| May-flat rows | 48 |
| Best May return | +0.037054 |
| Worst May return | -0.073293 |
| Median May return | 0.000000 |

The 48 flat rows are not confirmation; they had no May trades after fixed
pre-May filters. Active May selected rows were 10 positive and 42 negative.

Strict-row May behavior is a clear rejection:

| Strict subset metric | Value |
| --- | ---: |
| Strict rows benchmarked | 14 |
| Active strict May rows | 4 |
| Positive active strict May rows | 0 |
| Negative active strict May rows | 4 |
| Strict May mean return | -0.008743 |
| Strict active May mean return | -0.030600 |
| Strict active May worst return | -0.056170 |

The best May-positive selected row is loose, not strict:

- candidate: `adaptexit-c32211fc1e2a8ad7`;
- symbol: ETHUSDT;
- template: `vol_breakout_follow`;
- side mode: both actual anti-signal sides;
- regime filter: `all`;
- exit: `barrier_h32_tp2_sl1`;
- daily cap: 5;
- May trades: 76;
- May net return: +0.037054;
- May cost-stress survival: 2/4.

## Decision

WPR106-173 rejects the anti-signal entry/exit screen as candidate-ready,
portfolio-ready, or promotion-ready evidence despite finding 14 strict pre-May
rows. The strict rows fail the May benchmark: active strict rows are all
negative, and inactive strict rows provide no May confirmation.

Useful follow-up evidence: opposite-side ETH volatility-breakout anti-signals
with conservative ATR barriers are the first recent broad screen to produce
strict pre-May monthly stability rows. They should be treated as a research
diagnostic for a later fresh non-May retest, source-level controls, duplicate
deduplication, and May-regime failure analysis, not as candidate-ready evidence.

## Artifacts

- Runner:
  `data/research/wpr106_173_anti_signal_entry_exit_screen/scripts/run_wpr106_173_anti_signal_entry_exit_screen.py`
- Summary:
  `data/research/wpr106_173_anti_signal_entry_exit_screen/wpr106_173_anti_signal_entry_exit_summary.json`
- Ranking:
  `data/research/wpr106_173_anti_signal_entry_exit_screen/pre_may/anti_signal_entry_exit_ranking.parquet`
- Top 2000:
  `data/research/wpr106_173_anti_signal_entry_exit_screen/pre_may/anti_signal_entry_exit_top2000.csv`
- Monthly returns:
  `data/research/wpr106_173_anti_signal_entry_exit_screen/pre_may/anti_signal_entry_exit_monthly_returns.parquet`
- Selected rows and trades:
  `data/research/wpr106_173_anti_signal_entry_exit_screen/pre_may/selected_pre_may.parquet`
  and
  `data/research/wpr106_173_anti_signal_entry_exit_screen/pre_may/selected_pre_may_trades.parquet`
- May benchmark metrics and trades:
  `data/research/wpr106_173_anti_signal_entry_exit_screen/may_benchmark/selected_may_benchmark_metrics.parquet`
  and
  `data/research/wpr106_173_anti_signal_entry_exit_screen/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

Passed:

- `python -m compileall -q data\research\wpr106_173_anti_signal_entry_exit_screen\scripts`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`

Contract result: 460 passed.
