# Stage R106 Opening-Range Prior-Day Confluence Repair Report

Date: 2026-06-12
Work packet: WPR106-181-opening-range-prior-day-confluence-repair
Status: confluence repair completed, no May-confirmed lead

## Scope

WPR106-181 revisits two discarded but structurally distinct families:
WPR106-129 opening-range breakout/fade and WPR106-130 prior-day level/gap
behavior. WPR106-129 produced active pre-May diagnostics but every fixed
selected row lost in May. WPR106-130 produced one strict pre-May ETHUSDT
prior-day breakout row, but that fixed row failed May.

This packet tests a May-blind confluence repair: opening-range signals are
evaluated only through prior-day high/low/close, prior-day VWAP, overnight gap,
session, flow, and volatility context.

All thresholds, filters, daily caps, row inclusion, ranking, and selection use
only 2024-01-01 through 2026-04-30. May 2026 is replayed only after fixed
pre-May row selection.

This packet is research-only and observe-only. It writes no candidate pack,
paper/live artifact, live configuration, sizing change, order path, CUDA
speedup claim, or promotion claim.

## Method

Inputs:

- WPR106-126 source-context loading for WPR106-96 BTCUSDT/ETHUSDT 15m bars
  through May 2026;
- WPR106-126 15m aggTrade-flow aggregation;
- WPR106-126 cost, overlap, monthly, daily, and cost-stress accounting;
- WPR106-129 and WPR106-130 reports as negative source evidence.

The WPR106-181 runner evaluates:

- symbols: BTCUSDT and ETHUSDT;
- anchor sessions: Asia, EU, and US;
- opening-range lengths: 4, 8, and 16 completed 15m bars;
- fixed holds: 4, 8, 16, and 32 bars;
- volatility/volume filters: all, quiet-to-normal, high-volume, and
  high-range;
- flow filters: all, flow-confirmed, flow-contrarian, and flow-neutral;
- target raw signals: 1, 3, and 5 per active day;
- accepted-trade daily caps: 1, 3, and 5.

Confluence templates:

- `or_prior_breakout_confluence`;
- `or_prior_failed_break_fade`;
- `or_gap_continuation`;
- `or_gap_failure_reversion`;
- `or_prior_close_range_fade`.

Signals use completed 15m bars and enter on the next 15m open. Costs remain
0.0432% taker fee per side plus 0.0150% slippage/spread per side, for 0.001164
round-trip cost.

Runtime was 759.9 seconds. CUDA was not used and no speedup is claimed.

## Pre-May Results

Full confluence grid:

| Metric | Value |
| --- | ---: |
| Evaluated rows | 51,840 |
| Positive pre-May rows | 6,223 |
| Annual-target rows | 21 |
| Loose rows | 196 |
| Strict rows | 0 |

Selected fixed set:

| Metric | Value |
| --- | ---: |
| Selected rows | 100 |
| Dropout-repair rows | 19 |
| Loose rows | 81 |
| Positive selected pre-May rows | 100 |
| Negative selected pre-May rows | 0 |
| Median selected pre-May return | +0.486439 |
| Active mean selected pre-May return | +0.407773 |
| Best selected pre-May return | +0.751056 |
| Worst selected pre-May return | +0.044205 |

The annual-target rows are all ETHUSDT EU `or_gap_continuation` variants with
41 trades and 21 active months. They have attractive annual losing-month counts
but are too sparse for the requested active profile and do not qualify as
loose or strict.

Pre-May source summary:

| Symbol | Session | Template | Rows | Positive | Annual Target | Loose | Strict | Median | Best |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ETHUSDT | EU | `or_gap_continuation` | 1,728 | 1,065 | 21 | 144 | 0 | +0.077190 | +0.782466 |
| ETHUSDT | US | `or_prior_breakout_confluence` | 1,728 | 1,050 | 0 | 11 | 0 | +0.077184 | +0.751056 |
| ETHUSDT | EU | `or_prior_breakout_confluence` | 1,728 | 512 | 0 | 3 | 0 | -0.136261 | +0.736232 |
| ETHUSDT | US | `or_gap_continuation` | 1,728 | 915 | 0 | 9 | 0 | +0.012239 | +0.421929 |
| BTCUSDT | EU | `or_gap_failure_reversion` | 1,728 | 398 | 0 | 5 | 0 | -0.083690 | +0.283673 |
| BTCUSDT | Asia | `or_gap_failure_reversion` | 1,728 | 394 | 0 | 11 | 0 | -0.050649 | +0.114739 |

## May Benchmark

Fixed selected rows:

| Metric | May 2026 |
| --- | ---: |
| Rows | 100 |
| Active rows | 100 |
| Positive rows | 13 |
| Negative rows | 87 |
| Flat rows | 0 |
| Median return | -0.009593 |
| Active mean return | -0.009877 |
| Best return | +0.010523 |
| Worst return | -0.046390 |

By selection tier:

| Tier | Rows | May Positive | May Negative | May Median | May Mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| `dropout_repair` | 19 | 0 | 19 | -0.002965 | -0.005821 |
| `loose` | 81 | 13 | 68 | -0.011621 | -0.010829 |

By selected group:

| Symbol | Session | Template | Tier | Rows | May Pos/Neg | May Median | May Mean |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| ETHUSDT | EU | `or_gap_continuation` | loose | 48 | 13/35 | -0.005316 | -0.004604 |
| ETHUSDT | EU | `or_gap_continuation` | dropout_repair | 16 | 0/16 | -0.002965 | -0.005730 |
| BTCUSDT | Asia | `or_gap_failure_reversion` | loose | 11 | 0/11 | -0.011631 | -0.011866 |
| ETHUSDT | US | `or_prior_breakout_confluence` | loose | 11 | 0/11 | -0.020786 | -0.030350 |
| ETHUSDT | EU | `or_gap_failure_reversion` | loose | 6 | 0/6 | -0.027273 | -0.025841 |

Best May row:

- candidate: `orprior181-77a08befef97e8e2`;
- symbol/session/template: ETHUSDT EU `or_gap_continuation`;
- daily cap: 5;
- pre-May return: +0.604109;
- pre-May trades: 84;
- pre-May active months: 26;
- pre-May losing months: 8;
- annual losses: 2024 = 5, 2025 = 3, 2026 Jan-Apr = 0;
- May trades: 4;
- May return: +0.010523.

The best May row is not a candidate lead because it is loose-only, fails the
annual losing-month target, and belongs to a selected group with a negative May
median.

## Decision

WPR106-181 rejects the opening-range/prior-day confluence repair as
candidate-ready, portfolio-ready, or promotion-ready evidence.

The confluence repair improves on WPR106-129's all-negative May selected set by
finding a small May-positive ETHUSDT EU gap-continuation pocket. It still fails
the requested profile:

- zero strict pre-May rows;
- annual-target rows are too sparse at 41 trades;
- every `dropout_repair` selected row loses in May;
- selected May benchmark is 13 positive and 87 negative;
- May median and active mean are negative.

Useful diagnostics to preserve:

- ETHUSDT EU `or_gap_continuation` is a productive pre-May and partially
  May-positive clue, but it fails annual loss caps and selected-group transfer.
- ETHUSDT US `or_prior_breakout_confluence` is productive pre-May but fails
  May as a selected group.
- BTCUSDT gap-failure reversion remains loose/diagnostic only and does not
  transfer to May.

## Artifacts

- Runner:
  `data/research/wpr106_181_opening_range_prior_day_confluence_repair/scripts/run_wpr106_181_opening_range_prior_day_confluence_repair.py`
- Summary:
  `data/research/wpr106_181_opening_range_prior_day_confluence_repair/wpr106_181_opening_range_prior_day_confluence_repair_summary.json`
- Full ranking:
  `data/research/wpr106_181_opening_range_prior_day_confluence_repair/pre_may/or_prior_confluence_ranking.parquet`
- Monthly returns:
  `data/research/wpr106_181_opening_range_prior_day_confluence_repair/pre_may/or_prior_confluence_monthly_returns.parquet`
- Family/session summary:
  `data/research/wpr106_181_opening_range_prior_day_confluence_repair/pre_may/family_session_summary.parquet`
- Selected pre-May rows and replay:
  `data/research/wpr106_181_opening_range_prior_day_confluence_repair/pre_may/selected_pre_may.parquet`,
  `selected_pre_may_replay_metrics.parquet`,
  `selected_pre_may_monthly_returns.parquet`, and
  `selected_pre_may_trades.parquet`
- May benchmark:
  `data/research/wpr106_181_opening_range_prior_day_confluence_repair/may_benchmark/selected_may_benchmark_metrics.parquet`,
  `selected_may_benchmark_monthly_returns.parquet`, and
  `selected_may_benchmark_trades.parquet`
- Selected pre-May/May comparison:
  `data/research/wpr106_181_opening_range_prior_day_confluence_repair/selected_pre_may_may_comparison.parquet`

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_181_opening_range_prior_day_confluence_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contract result: 460 passed.
