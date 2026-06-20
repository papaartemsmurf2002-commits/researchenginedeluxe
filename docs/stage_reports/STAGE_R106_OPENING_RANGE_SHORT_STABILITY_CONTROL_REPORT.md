# Stage R106 WPR106-197 Opening-Range Short Stability Control Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-197 followed up the WPR106-196 ETHUSDT opening-range short diagnostic.
The prior packet found a real May-positive pocket, but it failed the requested
month-to-month stability profile with 10 pre-May losing months. WPR106-197
tested whether causal state filters, stronger pre-May score thresholds, and
prior-month health gates could reduce losing months without using May 2026 for
tuning.

All opening-window, hold, threshold, state-filter, health-gate, session,
daily-cap, ranking, and selected-row choices used only 2024-01-01 through
2026-04-30 UTC. May 2026 was benchmark-only after fixed pre-May selection.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_197_opening_range_short_stability_control/scripts/run_wpr106_197_opening_range_short_stability_control.py`

The runner imports WPR106-196/WPR106-170 helpers for aligned WPR106-96
BTCUSDT/ETHUSDT source context, ETHUSDT opening-range features, fixed-hold path
labels, WPR106 costs, completed-bar period masks, same-symbol overlap blocking,
accepted-trade daily caps, monthly metrics, and cost-stress diagnostics.

The search is restricted to ETHUSDT `opening_range_breakout_follow` short
behavior and evaluates:

- opening windows of 4, 8, and 16 completed 15m bars;
- 16, 24, 32, and 48 bar fixed holds;
- all/EU/US sessions;
- all, active-flow, downside-flow, bearish-trend, bearish-flow-trend,
  below-VWAP, controlled-downside-extension, and range-expansion-downside
  state filters;
- target raw signal rates of 1, 2, 3, and 5 per day;
- threshold multipliers 1.00, 1.15, 1.30, 1.50, and 2.00;
- accepted-trade daily caps of 1, 2, 3, and 5;
- prior-month health gates: none, prior month positive, rolling-3 positive,
  rolling-3 loss-count <= 1, rolling-6 positive, and rolling-6 loss-count <= 2.

Health gates are causal: a month can only be enabled from prior-month or
prior-rolling-month raw strategy behavior. May gate state is computed only from
pre-May history.

Runtime was 1,167.54 seconds. CUDA was not used and no speedup claim was made.

## Results

Pre-May screen:

- 138,240 evaluated rows.
- 73,904 positive pre-May rows.
- 28,568 annual-target rows.
- 1,966 loose rows.
- 0 strict rows.

Rows by health gate:

- `rolling_6_loss_count_le2`: 23,040 rows, 10,396 positive, 6,451 annual,
  212 loose, 0 strict.
- `rolling_3_loss_count_le1`: 23,040 rows, 12,832 positive, 6,399 annual,
  335 loose, 0 strict.
- `prev_month_positive`: 23,040 rows, 11,679 positive, 5,304 annual, 110
  loose, 0 strict.
- `rolling_3_positive`: 23,040 rows, 12,644 positive, 4,969 annual, 476 loose,
  0 strict.
- `rolling_6_positive`: 23,040 rows, 11,904 positive, 3,942 annual, 667 loose,
  0 strict.
- `none`: 23,040 rows, 14,449 positive, 1,503 annual, 166 loose, 0 strict.

Annual-target rows were often sparse: median active months across annual rows
was 4, and the maximum active-month count among annual rows was 22. That is
the main reason the family is not candidate-ready despite many annual-target
flags.

Fixed selected set:

- 100 selected rows, all `annual_target_control`.
- Health gates: 79 `prev_month_positive`, 21 `rolling_3_loss_count_le1`.
- State filters: 25 `controlled_downside_extension`, 18 `below_vwap`,
  15 `all`, 15 `range_expansion_downside`, 11 `bearish_trend`,
  7 `active_flow`, 6 `bearish_flow_trend`, and 3 `downside_flow`.

Selected pre-May replay:

- 100 positive rows, 0 negative rows, 0 flat rows.
- Median net return: +0.847369.
- Active mean net return: +0.845733.
- Best/worst selected rows: +1.105636 / +0.726895.

May 2026 benchmark replay:

- 62 active rows and 38 flat/inactive rows.
- 55 positive rows, 7 negative rows, 38 flat rows.
- Median net return: +0.004472.
- Active mean net return: +0.023551.
- Best/worst selected rows: +0.055974 / -0.006421.

May by health gate:

- `prev_month_positive`: 79 rows, 34 positive, 38 flat, median 0.000000.
- `rolling_3_loss_count_le1`: 21 rows, 21 positive, 0 flat, median +0.004472.

May by state filter:

- `controlled_downside_extension`: 25 rows, 22 positive, 3 flat, median
  +0.048785.
- `bearish_trend`: 11 rows, 10 positive, 1 flat, median +0.004472.
- `below_vwap`: 18 rows, 9 positive, 9 flat, median +0.002236.
- `downside_flow`: 3 rows, 0 positive, 1 flat, median -0.000891.

## Best May Diagnostic

The best May row is `or197-bc838835e95dc29d`, an ETHUSDT opening-range short
with:

- opening window: 4 completed 15m bars;
- hold: 32 bars;
- session: all;
- state filter: `controlled_downside_extension`;
- target raw signals: 3/day;
- threshold multiplier: 1.30;
- daily cap: 3;
- health gate: `prev_month_positive`.

Pre-May:

- 73 trades over 57 active days;
- 16 active months and 12 inactive months;
- total net return +0.787461;
- expectancy +0.010787 per trade;
- max drawdown -0.073845;
- Sortino +1.157944;
- best-month share 0.223827;
- 100% cost-stress survival;
- 3 losing active months: one in 2024, two in 2025, zero in 2026 Jan-Apr.

May benchmark:

- 6 trades over 4 active days;
- total net return +0.055974;
- max drawdown -0.005238;
- no losing May month.

Monthly pre-May behavior shows the repair improved the losing-month count by
turning the strategy off in weak periods, not by proving stable full-time
activity. That is useful but insufficient for candidate readiness.

## Side Controls

For the fixed selected short rows, WPR106-197 replayed long-only and both-sided
controls with matching parameters and their own causal health gates.

- Long controls: 100 rows, 15 May-positive, 80 May-flat, May median 0.000000,
  May mean -0.000273, pre-May median -0.027666.
- Both-sided controls: 100 rows, 59 May-positive, 39 May-flat, May median
  +0.004472, May mean +0.014965, pre-May median +0.791980.

The long-only control is weak, supporting short-side asymmetry. The both-sided
control is not a strong negative control because it inherits most of the same
short trades; it should be treated as a behavior-overlap diagnostic, not an
independent confirmation.

## Interpretation

WPR106-197 is a meaningful improvement over WPR106-196. It moves the selected
May benchmark from negative median/mean to positive median/active mean, reduces
selected May losses to 7 negative rows out of 100, and identifies an ETHUSDT
controlled-downside-extension short pocket with low drawdown and positive May
transfer.

It is still not candidate-ready, portfolio-ready, or promotion-ready. The
decisive blockers are:

- 0 strict pre-May rows;
- selected rows rely on health gates that create many inactive months;
- the best May row has only 16 active pre-May months;
- many annual-target rows are sparse, with median active months of only 4;
- both-sided controls overlap heavily with the selected short behavior.

The useful next step is a narrower WPR106-198-style confirmation packet that
deduplicates behavior, requires higher active-month coverage, tests the
controlled-downside-extension short pocket against stronger no-trade/long
controls, and audits whether the prior-month health gate is robust rather than
just an inactivity filter.

## Artifacts

- `data/research/wpr106_197_opening_range_short_stability_control/pre_may/opening_range_short_pre_may_ranking.parquet`
- `data/research/wpr106_197_opening_range_short_stability_control/pre_may/opening_range_short_pre_may_ranking.csv`
- `data/research/wpr106_197_opening_range_short_stability_control/pre_may/opening_range_short_pre_may_monthly_returns.parquet`
- `data/research/wpr106_197_opening_range_short_stability_control/pre_may/selected_pre_may_rows.parquet`
- `data/research/wpr106_197_opening_range_short_stability_control/pre_may/selected_pre_may_rows.csv`
- `data/research/wpr106_197_opening_range_short_stability_control/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_197_opening_range_short_stability_control/pre_may/selected_pre_may_replay_metrics.csv`
- `data/research/wpr106_197_opening_range_short_stability_control/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_197_opening_range_short_stability_control/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_197_opening_range_short_stability_control/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_197_opening_range_short_stability_control/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_197_opening_range_short_stability_control/may_benchmark/selected_may_benchmark_metrics.csv`
- `data/research/wpr106_197_opening_range_short_stability_control/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_197_opening_range_short_stability_control/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_197_opening_range_short_stability_control/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_197_opening_range_short_stability_control/controls/selected_side_control_metrics.parquet`
- `data/research/wpr106_197_opening_range_short_stability_control/controls/selected_side_control_metrics.csv`
- `data/research/wpr106_197_opening_range_short_stability_control/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_197_opening_range_short_stability_control/selected_pre_may_may_comparison.csv`
- `data/research/wpr106_197_opening_range_short_stability_control/wpr106_197_opening_range_short_stability_control_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_197_opening_range_short_stability_control\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
