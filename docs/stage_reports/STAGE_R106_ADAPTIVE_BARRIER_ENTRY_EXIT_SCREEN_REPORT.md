# Stage R106 Adaptive Barrier Entry/Exit Screen Report

Date: 2026-06-12
Work packet: WPR106-172-adaptive-barrier-entry-exit-screen
Status: broad entry/exit screen completed, no candidate-ready lead

## Scope

WPR106-172 continues the 2024-forward broad search after WPR106-171 rejected
the market-state regime-gated repair overlay. This packet is a fresh source
screen rather than a prior-trade repair pass: it builds completed-bar entry
families directly from WPR106-96 BTCUSDT/ETHUSDT public-archive context and
tests fixed-hold plus conservative ATR barrier exits.

All entry thresholds, regime filters, exit choices, daily caps, ranking, and
selection use only 2024-01-01 through 2026-04-30. May 2026 is replayed only
after fixed pre-May rows are selected.

This packet is research-only and observe-only. It writes no candidate pack,
paper/live artifact, live configuration, sizing change, order path, CUDA
speedup claim, or promotion claim.

## Method

Inputs:

- WPR106-96 BTCUSDT/ETHUSDT 15m bars from 2024-01-01 through 2026-05-31;
- WPR106-96 BTCUSDT/ETHUSDT 1m aggTrade rows aggregated into completed 15m
  flow-pressure features.

Entry templates:

- `trend_pullback_follow`;
- `range_reversion_fade`;
- `vol_breakout_follow`;
- `wick_sweep_reversal`;
- `flow_price_divergence_fade`;
- `flow_burst_follow`;
- `compression_breakout_follow`.

Grid dimensions after the bounded runtime narrowing:

- symbols: BTCUSDT and ETHUSDT;
- normalization windows: 96 and 384 bars;
- sessions: all and US;
- regime filters: all, high-volatility, flow-confirm, flow-contra, and
  range-compression;
- side modes: both, long-only, and short-only;
- target raw signal rates: 1, 3, and 5 per active day;
- exits: fixed 16, 32, and 64 bars plus ATR barrier `h16 tp1/sl1` and
  `h32 tp2/sl1`;
- accepted-trade daily caps: 1, 3, and 5.

ATR barriers use the completed signal-bar ATR estimate. If a stop and target
are both reachable within the same bar, the stop is counted first. This avoids
profiting from unknown intrabar ordering. Costs are 0.0432% taker fee per side
plus 0.0150% slippage/spread per side, or 0.001164 round trip. Cost stress uses
1.0x, 1.25x, 1.5x, and 2.0x cost multipliers.

The runner completed in 468.5 seconds. CUDA was not used and no speedup is
claimed.

## Results

Full pre-May grid:

| Metric | Value |
| --- | ---: |
| Evaluated rows | 35,550 |
| Positive pre-May rows | 5,072 |
| Annual-target rows | 190 |
| Loose rows | 71 |
| Strict rows | 0 |

The fixed selected set contains only loose rows:

| Selected metric | Value |
| --- | ---: |
| Selected rows | 71 |
| Strict rows | 0 |
| Loose rows | 71 |
| Best pre-May net return | +1.114763 |
| Median pre-May net return | +0.319864 |
| Worst pre-May net return | +0.057242 |

The top stability-scored selected row is:

- candidate: `adaptexit-bbcba81756c33807`;
- symbol: ETHUSDT;
- template: `flow_burst_follow`;
- regime filter: `all`;
- exit: `fixed_64`;
- daily cap: 1;
- pre-May trades: 321;
- active months: 28;
- losing months: 8;
- annual losses: 2024: 4, 2025: 3, 2026 Jan-Apr: 1;
- pre-May net return: +1.114763;
- max drawdown: -0.220110;
- best-month share: 0.113607;
- cost-stress survival: 4/4.

It is not strict because it misses the annual loss-count and total
losing-month stability targets.

Template summary:

| Template | Positive rows | Annual-target rows | Loose rows | Median net | Best net |
| --- | ---: | ---: | ---: | ---: | ---: |
| `flow_burst_follow` | 1,181 | 0 | 21 | -0.178138 | +1.597790 |
| `vol_breakout_follow` | 1,313 | 184 | 18 | -0.171420 | +2.058576 |
| `range_reversion_fade` | 381 | 6 | 18 | -0.281025 | +0.590057 |
| `trend_pullback_follow` | 968 | 0 | 12 | -0.231017 | +0.911802 |
| `compression_breakout_follow` | 367 | 0 | 2 | -0.490693 | +1.260330 |
| `flow_price_divergence_fade` | 632 | 0 | 0 | -0.313733 | +0.671880 |
| `wick_sweep_reversal` | 230 | 0 | 0 | -0.602091 | +0.666908 |

Exit summary:

| Exit | Positive rows | Annual-target rows | Loose rows | Median net | Best net |
| --- | ---: | ---: | ---: | ---: | ---: |
| `barrier_h32_tp2_sl1` | 1,157 | 20 | 43 | -0.224511 | +0.661269 |
| `fixed_64` | 1,811 | 51 | 17 | -0.229101 | +2.058576 |
| `fixed_32` | 1,325 | 54 | 9 | -0.320230 | +1.597790 |
| `fixed_16` | 756 | 48 | 2 | -0.386868 | +0.943153 |
| `barrier_h16_tp1_sl1` | 23 | 17 | 0 | -0.455328 | +0.071192 |

## May Benchmark

May 2026 was benchmark-only after fixed pre-May selection:

| Metric | Value |
| --- | ---: |
| Selected rows benchmarked | 71 |
| May-positive rows | 5 |
| May-negative rows | 10 |
| May-flat rows | 56 |
| Best May return | +0.022584 |
| Worst May return | -0.074505 |
| Median May return | 0.000000 |

The 56 flat rows are not confirmation; they had no May trades after the fixed
pre-May threshold/filter/exit stack. Among the 15 active May rows, mean return
was -0.012550 and the median active return was -0.005730.

The best May-positive diagnostic row is:

- candidate: `adaptexit-2854df40bf9f26de`;
- symbol: ETHUSDT;
- template: `vol_breakout_follow`;
- regime filter: `flow_confirm`;
- exit: `fixed_64`;
- daily cap: 3;
- pre-May net return: +0.541153;
- pre-May active months: 28;
- pre-May losing months: 8;
- pre-May max drawdown: -0.278087;
- May trades: 13;
- May net return: +0.022584;
- May cost-stress survival: 4/4.

It remains diagnostic only because the aggregate selected set is mostly
inactive in May, active May rows are negative on average, and no strict pre-May
row exists.

## Decision

WPR106-172 rejects the adaptive barrier entry/exit screen as candidate-ready,
portfolio-ready, or promotion-ready evidence. The screen finds loose pre-May
pockets in ETH flow-burst, volatility-breakout, and range-reversion rows, but
they fail month-to-month stability and do not transfer strongly to May 2026.

Useful negative evidence: conservative ATR barriers did not repair broad entry
families enough to produce a strict row. The only May-positive pocket is a
small ETH volatility-breakout/flow-confirm fixed-hold diagnostic and should not
be defended without a fresh non-May holdout, stronger duplicate controls, and
stricter monthly stability.

## Artifacts

- Runner:
  `data/research/wpr106_172_adaptive_barrier_entry_exit_screen/scripts/run_wpr106_172_adaptive_barrier_entry_exit_screen.py`
- Summary:
  `data/research/wpr106_172_adaptive_barrier_entry_exit_screen/wpr106_172_adaptive_barrier_entry_exit_summary.json`
- Ranking:
  `data/research/wpr106_172_adaptive_barrier_entry_exit_screen/pre_may/adaptive_barrier_entry_exit_ranking.parquet`
- Top 2000:
  `data/research/wpr106_172_adaptive_barrier_entry_exit_screen/pre_may/adaptive_barrier_entry_exit_top2000.csv`
- Monthly returns:
  `data/research/wpr106_172_adaptive_barrier_entry_exit_screen/pre_may/adaptive_barrier_entry_exit_monthly_returns.parquet`
- Selected rows and trades:
  `data/research/wpr106_172_adaptive_barrier_entry_exit_screen/pre_may/selected_pre_may.parquet`
  and
  `data/research/wpr106_172_adaptive_barrier_entry_exit_screen/pre_may/selected_pre_may_trades.parquet`
- May benchmark metrics and trades:
  `data/research/wpr106_172_adaptive_barrier_entry_exit_screen/may_benchmark/selected_may_benchmark_metrics.parquet`
  and
  `data/research/wpr106_172_adaptive_barrier_entry_exit_screen/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

Passed:

- `python -m compileall -q data\research\wpr106_172_adaptive_barrier_entry_exit_screen\scripts`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`

Contract result: 460 passed.
