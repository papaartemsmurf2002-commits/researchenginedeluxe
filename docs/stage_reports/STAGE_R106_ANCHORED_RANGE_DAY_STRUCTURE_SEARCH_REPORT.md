# Stage R106 WPR106-196 Anchored Range Day-Structure Search Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-196 continued the broad 2024-forward research search after WPR106-195
rejected BTC/ETH residual pair spreads. It tested a fresh transparent
completed-bar entry family built from prior-day levels, opening ranges,
rolling multi-day range location, intraday VWAP residual, completed-bar flow,
wick, volume, and volatility state.

All feature thresholds, state filters, hold/session/side/daily-cap choices,
row ranking, and selected-row inclusion used only 2024-01-01 through
2026-04-30 UTC. May 2026 was benchmark-only after fixed pre-May selection.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_196_anchored_range_day_structure_search/scripts/run_wpr106_196_anchored_range_day_structure_search.py`

The runner imports the WPR106-170 helper module for aligned WPR106-96
BTCUSDT/ETHUSDT 15m plus aggTrade-flow context, completed-bar period masks,
future fixed-hold path labels, WPR106 cost constants, overlap handling,
accepted-trade daily caps, monthly metrics, and cost-stress diagnostics.

It builds causal day-structure features from completed bars only:

- shifted prior-day high, low, open, close, range, and return;
- completed opening-range high/low after the opening window is known;
- current day high/low so far and intraday VWAP residual;
- shifted 5-day and 20-day range location;
- day-open gap state;
- completed-bar return, flow, flow momentum, wick, volume, realized volatility,
  and range z-scores.

Templates covered prior-day breakout follow/fade, opening-range breakout
follow/fade, gap-fill reversion, session-VWAP reversion, rolling-range
reversion, and liquidity-sweep fades. The final run used template-relevant
anchor variants only: opening-range and sweep templates vary opening-window
length, rolling-range templates vary shifted range length, and prior-day,
gap-fill, and VWAP templates do not repeat across irrelevant anchor knobs.

An initial unclosed run showed that evaluating every template across every
opening/rolling anchor duplicated prior-day and VWAP trade paths. The runner
was corrected before final evidence. The final authoritative run evaluated
51,840 rows in 431.94 seconds. CUDA was not used and no speedup claim was made.

## Results

Pre-May screen:

- 51,840 evaluated rows.
- 8,900 positive pre-May rows.
- 1,458 annual-target rows.
- 85 loose rows.
- 0 strict rows.

Rows by template:

- `opening_range_breakout_fade`: 10,368 rows, 1,414 positive, 627
  annual-target, 10 loose, 0 strict.
- `opening_range_breakout_follow`: 10,368 rows, 2,962 positive, 465
  annual-target, 25 loose, 0 strict.
- `gap_fill_reversion`: 3,456 rows, 605 positive, 129 annual-target, 6 loose,
  0 strict.
- `rolling_range_reversion`: 6,912 rows, 799 positive, 114 annual-target,
  12 loose, 0 strict.
- `session_vwap_reversion`: 3,456 rows, 372 positive, 65 annual-target,
  0 loose, 0 strict.
- `liquidity_sweep_fade`: 10,368 rows, 1,439 positive, 24 annual-target,
  17 loose, 0 strict.
- `prior_day_breakout_follow`: 3,456 rows, 1,092 positive, 24 annual-target,
  15 loose, 0 strict.
- `prior_day_breakout_fade`: 3,456 rows, 217 positive, 10 annual-target,
  0 loose, 0 strict.

Fixed selected set:

- 100 selected rows.
- 92 `positive_recent_stability` rows and 8 `loose_recent` rows.
- 100 ETHUSDT rows and 0 BTCUSDT rows.
- 72 `opening_range_breakout_follow` rows and 28
  `prior_day_breakout_follow` rows.
- State filters: 35 `active_flow`, 33 `range_expansion`, and 32 `all`.

Selected pre-May replay:

- 100 positive rows, 0 negative rows, 0 flat rows.
- Median net return: +0.856864.
- Active mean net return: +0.876398.
- Best/worst selected rows: +1.196304 / +0.597246.

May 2026 benchmark replay:

- 100 active rows.
- 36 positive rows, 64 negative rows, 0 flat rows.
- Median net return: -0.007769.
- Active mean net return: -0.009575.
- Best/worst selected rows: +0.062069 / -0.052891.

May by selected template:

- `opening_range_breakout_follow`: 72 rows, 28 positive, median -0.007101,
  mean -0.007080.
- `prior_day_breakout_follow`: 28 rows, 8 positive, median -0.007769,
  mean -0.015989.

May by side mode:

- `short`: 9 rows, 6 positive, median +0.035949.
- `both`: 91 rows, 30 positive, median -0.010410.

## Best May Diagnostic

The best May row is `day196-b707d26e4b8fa963`, an ETHUSDT
`opening_range_breakout_follow` short-only row:

- opening window: 4 completed 15m bars;
- shifted rolling range: 5 days;
- hold: 32 bars;
- session: all;
- state filter: all;
- target raw signals: 5/day;
- accepted-trade daily cap: 1;
- pre-May threshold: 3.045907735824585.

Pre-May:

- 176 trades over 176 active days;
- 28 active months;
- total net return +1.006399;
- max drawdown -0.150763;
- best-month share 0.211052;
- 100% cost-stress survival;
- 10 losing months: five in 2024, four in 2025, one in 2026 Jan-Apr.

May benchmark:

- 7 trades over 7 active days;
- total net return +0.062069;
- max drawdown -0.005090;
- two losing active days inside May.

This is a useful diagnostic pocket because it is active and May-positive with
lower drawdown than many prior leads. It is not candidate-ready because it
fails the desired annual/monthly stability profile: five losing months in
2024, four in 2025, and ten losing pre-May months overall.

## Interpretation

Anchored range/day-structure entries produce a stronger pre-May transparent
signal family than the immediately preceding spread and motif repairs, and
they produce a real May-positive ETHUSDT opening-range short pocket. However,
the fixed selected set is still not stable enough: zero strict rows, selected
May median and mean are negative, and the best May row fails the requested
month-to-month stability target.

WPR106-196 therefore rejects the anchored range/day-structure family as
candidate-ready, portfolio-ready, or promotion-ready. The useful next clue is
not broad acceptance of this family; it is a narrower ETHUSDT opening-range
breakout short follow-up with stronger monthly-stability filters, behavior
deduplication, and controls against the corresponding long/both-sided variants.

## Artifacts

- `data/research/wpr106_196_anchored_range_day_structure_search/pre_may/anchored_day_structure_pre_may_ranking.parquet`
- `data/research/wpr106_196_anchored_range_day_structure_search/pre_may/anchored_day_structure_pre_may_ranking.csv`
- `data/research/wpr106_196_anchored_range_day_structure_search/pre_may/anchored_day_structure_pre_may_monthly_returns.parquet`
- `data/research/wpr106_196_anchored_range_day_structure_search/pre_may/selected_pre_may_rows.parquet`
- `data/research/wpr106_196_anchored_range_day_structure_search/pre_may/selected_pre_may_rows.csv`
- `data/research/wpr106_196_anchored_range_day_structure_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_196_anchored_range_day_structure_search/pre_may/selected_pre_may_replay_metrics.csv`
- `data/research/wpr106_196_anchored_range_day_structure_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_196_anchored_range_day_structure_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_196_anchored_range_day_structure_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_196_anchored_range_day_structure_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_196_anchored_range_day_structure_search/may_benchmark/selected_may_benchmark_metrics.csv`
- `data/research/wpr106_196_anchored_range_day_structure_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_196_anchored_range_day_structure_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_196_anchored_range_day_structure_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_196_anchored_range_day_structure_search/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_196_anchored_range_day_structure_search/selected_pre_may_may_comparison.csv`
- `data/research/wpr106_196_anchored_range_day_structure_search/wpr106_196_anchored_range_day_structure_search_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_196_anchored_range_day_structure_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
