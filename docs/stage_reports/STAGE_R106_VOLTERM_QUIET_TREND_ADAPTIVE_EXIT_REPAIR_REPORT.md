# Stage R106 Volatility-Term Quiet-Trend Adaptive Exit Repair Report

Date: 2026-06-12
Work packet: WPR106-180-volterm-quiet-trend-adaptive-exit-repair
Status: repair search completed, no May-confirmed lead

## Scope

WPR106-180 revisits the discarded WPR106-131 realized-volatility
term-structure family. WPR106-131 had one annual-loss-compliant ETHUSDT
quiet-trend pullback diagnostic, but no strict rows and a failed May benchmark
for the loose selected set.

This packet tests whether a May-blind repair can raise active coverage and
stability by focusing on quiet-trend pullback, volatility-expansion follow,
compression-breakout follow, volatility-shock fade, and term-structure
reversal variants with adaptive exits and daily caps.

All thresholds, filters, exit policies, daily caps, row inclusion, ranking, and
selection use only 2024-01-01 through 2026-04-30. May 2026 is replayed only
after fixed pre-May row selection. June 1-11 2026 is not replayed because the
WPR106-131/WPR106-126 source context used by this packet is available through
May 2026 only.

This packet is research-only and observe-only. It writes no candidate pack,
paper/live artifact, live configuration, sizing change, order path, CUDA
speedup claim, or promotion claim.

## Method

Inputs:

- WPR106-131 volatility-term score construction and completed-bar alignment;
- WPR106-126/WPR106-96 BTCUSDT and ETHUSDT 15m bar context through May 2026;
- WPR106-126 15m aggTrade-flow aggregation;
- WPR106-126 accounting for costs, overlap handling, monthly metrics, daily
  downside metrics, and cost stress.

The WPR106-180 runner evaluates:

- symbols: BTCUSDT and ETHUSDT;
- realized-volatility windows: 96, 384, and 1,536 bars;
- templates: `quiet_trend_pullback`, `vol_expansion_follow`,
  `compression_breakout_follow`, `vol_shock_fade`, and
  `term_structure_reversal`;
- max holds: 8, 16, 32, and 64 bars;
- sessions: all and US;
- volatility regimes: all, compressed, and expanding;
- flow filters: all, flow-confirmed, flow-contrarian, and flow-neutral;
- target raw signals: 1, 3, and 5 per active day;
- accepted-trade daily caps: 1, 3, and 5;
- exits: fixed, fast score decay, half score decay, flip/loss guard, and
  volatility loss guard.

Adaptive exits are causal over completed bars: entry uses the next 15m open
after a completed signal bar, and adaptive exit checks use only completed bars
before the exit open. Costs remain 0.0432% taker fee per side plus 0.0150%
slippage/spread per side, for 0.001164 round-trip cost.

The runner cached feature arrays by symbol/window and reused calibrated signal
sets across daily-cap and exit-policy variants. Runtime was 2,720.0 seconds.
CUDA was not used and no speedup is claimed.

## Pre-May Results

Full repair grid:

| Metric | Value |
| --- | ---: |
| Evaluated rows | 129,600 |
| Positive pre-May rows | 18,762 |
| Annual-target rows | 1,270 |
| Loose rows | 391 |
| Strict rows | 0 |

Selected fixed set:

| Metric | Value |
| --- | ---: |
| Selected rows | 100 |
| Dropout-repair rows | 11 |
| Loose rows | 89 |
| Positive selected pre-May rows | 100 |
| Negative selected pre-May rows | 0 |
| Median selected pre-May return | +0.601534 |
| Active mean selected pre-May return | +0.599311 |
| Best selected pre-May return | +1.293790 |
| Worst selected pre-May return | +0.038192 |

The annual-target count is not enough. Most annual-target rows are too sparse
to satisfy the requested active profile. The only annual-target loose rows are
ETHUSDT `quiet_trend_pullback` fixed or fast score-decay variants with 62 to
64 trades, 23 active months, four losing months, and full cost-stress survival.

Pre-May source/exit summary, sorted by annual-target rows:

| Symbol | Template | Exit | Rows | Positive | Annual Target | Loose | Strict | Median | Best |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ETHUSDT | `compression_breakout_follow` | fixed | 2,592 | 507 | 192 | 0 | 0 | 0.000000 | +0.541848 |
| ETHUSDT | `compression_breakout_follow` | score_decay_half | 2,592 | 432 | 177 | 0 | 0 | -0.009346 | +0.410354 |
| ETHUSDT | `compression_breakout_follow` | flip_or_loss_guard | 2,592 | 380 | 177 | 0 | 0 | -0.034459 | +0.221557 |
| ETHUSDT | `compression_breakout_follow` | vol_loss_guard | 2,592 | 486 | 168 | 4 | 0 | 0.000000 | +0.970983 |
| ETHUSDT | `compression_breakout_follow` | score_decay_fast | 2,592 | 351 | 165 | 0 | 0 | -0.040339 | +0.232016 |
| BTCUSDT | `compression_breakout_follow` | vol_loss_guard | 2,592 | 325 | 95 | 0 | 0 | -0.028156 | +0.270323 |
| BTCUSDT | `compression_breakout_follow` | fixed | 2,592 | 326 | 84 | 0 | 0 | -0.024015 | +0.491306 |
| ETHUSDT | `vol_expansion_follow` | fixed | 2,592 | 1,442 | 3 | 31 | 0 | +0.051491 | +1.678504 |
| ETHUSDT | `quiet_trend_pullback` | fixed | 2,592 | 1,168 | 2 | 23 | 0 | -0.033674 | +1.357933 |
| ETHUSDT | `quiet_trend_pullback` | score_decay_fast | 2,592 | 961 | 2 | 29 | 0 | -0.081026 | +1.008167 |

## May Benchmark

Fixed selected rows:

| Metric | May 2026 |
| --- | ---: |
| Rows | 100 |
| Active rows | 100 |
| Positive rows | 12 |
| Negative rows | 88 |
| Flat rows | 0 |
| Median return | -0.009113 |
| Active mean return | -0.014822 |
| Best return | +0.077562 |
| Worst return | -0.108927 |

By selection tier:

| Tier | Rows | May Positive | May Negative | May Median | May Mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| `dropout_repair` | 11 | 0 | 11 | -0.007953 | -0.016409 |
| `loose` | 89 | 12 | 77 | -0.009113 | -0.014626 |

By selected template/exit:

| Symbol | Template | Exit | Tier | Rows | May Pos/Neg | May Median | May Mean |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| ETHUSDT | `vol_expansion_follow` | fixed | loose | 20 | 7/13 | -0.012070 | -0.016066 |
| ETHUSDT | `quiet_trend_pullback` | fixed | loose | 8 | 0/8 | -0.021084 | -0.029365 |
| ETHUSDT | `vol_shock_fade` | score_decay_half | loose | 6 | 0/6 | -0.001064 | -0.001161 |
| ETHUSDT | `vol_expansion_follow` | score_decay_half | loose | 6 | 0/6 | -0.021051 | -0.021051 |
| ETHUSDT | `quiet_trend_pullback` | score_decay_half | loose | 6 | 0/6 | -0.033291 | -0.033326 |
| ETHUSDT | `vol_shock_fade` | score_decay_fast | loose | 5 | 2/3 | -0.001255 | +0.000907 |
| ETHUSDT | `compression_breakout_follow` | vol_loss_guard | loose | 4 | 0/4 | -0.004036 | -0.004036 |

Best May row:

- candidate: `volterm180-5cd0fff3173532a4`;
- symbol/template: ETHUSDT `vol_expansion_follow`;
- exit: fixed;
- daily cap: 1;
- pre-May return: +1.079938;
- pre-May trades: 354;
- pre-May active months: 28;
- pre-May losing months: 8;
- annual losses: 2024 = 3, 2025 = 3, 2026 Jan-Apr = 2;
- May trades: 14;
- May return: +0.077562.

The best May row is not a candidate lead because it is loose-only, misses all
annual loss caps, and belongs to a selected group with a negative May median.

## Decision

WPR106-180 rejects the volatility-term quiet-trend adaptive-exit repair as
candidate-ready, portfolio-ready, or promotion-ready evidence.

The packet makes a fairer repair attempt than WPR106-131 by adding daily caps,
score-decay exits, loss-guard exits, and volatility-loss exits. It increases
positive pre-May rows and finds many annual-target diagnostics, but the central
problem remains:

- zero strict pre-May rows;
- annual-target rows are generally too sparse for the requested active profile;
- all 11 `dropout_repair` selected rows lose in May;
- the fixed selected set is 12 positive and 88 negative in May;
- May median and active mean are negative.

Useful diagnostics to preserve:

- ETHUSDT `vol_expansion_follow` fixed-hold rows can be May-positive, but they
  miss annual losing-month caps and fail as a selected group.
- ETHUSDT `quiet_trend_pullback` remains the only active annual-target loose
  pocket, but its fixed selected rows lose in May.
- Compression-breakout annual-target rows are mostly too sparse, even when
  adaptive exits improve annual loss counts.

## Artifacts

- Runner:
  `data/research/wpr106_180_volterm_quiet_trend_adaptive_exit_repair/scripts/run_wpr106_180_volterm_quiet_trend_adaptive_exit_repair.py`
- Summary:
  `data/research/wpr106_180_volterm_quiet_trend_adaptive_exit_repair/wpr106_180_volterm_quiet_trend_adaptive_exit_repair_summary.json`
- Full ranking:
  `data/research/wpr106_180_volterm_quiet_trend_adaptive_exit_repair/pre_may/volterm_repair_ranking.parquet`
- Monthly returns:
  `data/research/wpr106_180_volterm_quiet_trend_adaptive_exit_repair/pre_may/volterm_repair_monthly_returns.parquet`
- Family/exit summary:
  `data/research/wpr106_180_volterm_quiet_trend_adaptive_exit_repair/pre_may/family_exit_summary.parquet`
- Selected pre-May rows and replay:
  `data/research/wpr106_180_volterm_quiet_trend_adaptive_exit_repair/pre_may/selected_pre_may.parquet`,
  `selected_pre_may_replay_metrics.parquet`,
  `selected_pre_may_monthly_returns.parquet`, and
  `selected_pre_may_trades.parquet`
- May benchmark:
  `data/research/wpr106_180_volterm_quiet_trend_adaptive_exit_repair/may_benchmark/selected_may_benchmark_metrics.parquet`,
  `selected_may_benchmark_monthly_returns.parquet`, and
  `selected_may_benchmark_trades.parquet`
- Selected pre-May/May comparison:
  `data/research/wpr106_180_volterm_quiet_trend_adaptive_exit_repair/selected_pre_may_may_comparison.parquet`

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_180_volterm_quiet_trend_adaptive_exit_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contract result: 460 passed.
