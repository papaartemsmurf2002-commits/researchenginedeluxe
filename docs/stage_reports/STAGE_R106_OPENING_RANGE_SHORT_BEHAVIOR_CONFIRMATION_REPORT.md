# Stage R106 WPR106-198 Opening-Range Short Behavior Confirmation Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-198 followed up the WPR106-197 ETHUSDT opening-range short repair.
WPR106-197 improved May transfer, but it relied on causal prior-month health
gates that created many inactive months. This packet tested whether exact
accepted-trade behavior deduplication, higher active-month coverage, and
health-gate controls confirmed a robust short-side pocket without using May
2026 for tuning.

Source-pool filtering, replay, behavior hashes, ranking, selected-row
inclusion, and controls used only 2024-01-01 through 2026-04-30 UTC. May 2026
was benchmark-only after the fixed selected set existed.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_198_opening_range_short_behavior_confirmation/scripts/run_wpr106_198_opening_range_short_behavior_confirmation.py`

The runner imports WPR106-197 helpers and reads the WPR106-197 pre-May ranking
artifact. It builds a May-blind ETHUSDT short source pool, replays source rows
on pre-May data, computes exact accepted-trade path hashes, behavior-dedupes
rows, ranks representatives by active-month coverage and month-stability
evidence, and only then replays May 2026 for the fixed selected set.

Controls for the selected rows are:

- no-health-gate ablation;
- inverted-health-gate diagnostic;
- long-only side control;
- both-sided overlap diagnostic;
- no-trade baseline.

Runtime was 37.33 seconds. CUDA was not used and no speedup claim was made.

## Results

Pre-May source and selection:

- 1,818 WPR106-197 source-pool rows replayed.
- 1,011 exact behavior-deduped representatives.
- 100 selected rows.
- Selected tiers: 81 `deduped_health_repair` and 19
  `active_month_confirmation`.
- Selected health gates: 33 `rolling_6_positive`, 24
  `rolling_3_loss_count_le1`, 16 `rolling_3_positive`, 15
  `rolling_6_loss_count_le2`, and 12 `prev_month_positive`.

Source-pool pre-May replay:

- 1,818 positive rows, zero negative rows, zero flat rows.
- Median net return: +0.616750.
- Active mean net return: +0.625401.
- Best/worst rows: +1.105636 / +0.400133.

Behavior-deduped pre-May replay:

- 1,011 positive rows, zero negative rows, zero flat rows.
- Median net return: +0.626552.
- Active mean net return: +0.634197.
- Best/worst rows: +1.105636 / +0.400133.

Fixed selected pre-May replay:

- 100 positive rows, zero negative rows, zero flat rows.
- Median net return: +0.736564.
- Active mean net return: +0.720171.
- Best/worst selected rows: +1.030453 / +0.431305.
- Median active months: 20; median losing months: 5.
- 19 annual-target rows, 96 loose rows, and zero strict rows.

May 2026 benchmark:

- 84 active rows and 16 flat/inactive rows.
- 48 positive rows, 36 negative rows, 16 flat rows.
- Median net return: 0.000000.
- Active mean net return: +0.008183.
- Best/worst selected rows: +0.056746 / -0.048005.

May by selected tier:

- `deduped_health_repair`: 81 rows, 73 active, 41 positive, 32 negative,
  eight flat, median +0.000928, active mean +0.009619.
- `active_month_confirmation`: 19 rows, 11 active, seven positive,
  four negative, eight flat, median 0.000000, active mean -0.001351.

May by health gate:

- `rolling_3_loss_count_le1`: 24 rows, 23 active, 18 positive, five negative,
  one flat, median +0.004472.
- `rolling_6_positive`: 33 rows, 33 active, 17 positive, 16 negative,
  zero flat, median +0.002218.
- `rolling_3_positive`: 16 rows, 13 active, six positive, seven negative,
  three flat, median 0.000000.
- `rolling_6_loss_count_le2`: 15 rows, 14 active, six positive, eight
  negative, one flat, median -0.003969.
- `prev_month_positive`: 12 rows, one active positive row and 11 flat rows,
  median 0.000000.

## Controls

The no-health ablation is the important control result.

- `no_health`: 100 May-active rows, 58 positive, 42 negative, zero flat,
  pre-May median +0.837633, May median +0.004472, May active mean +0.007535.
- `inverse_health`: 76 May-active rows, 39 positive, 37 negative, 24 flat,
  pre-May median +0.668682, May median 0.000000, May active mean +0.005811.
- `both_control`: 54 May-active rows, 40 positive, 14 negative, 46 flat,
  pre-May median +0.602933, May median 0.000000, May active mean +0.016774.
- `long_control`: 27 May-active rows, 11 positive, 16 negative, 73 flat,
  pre-May median -0.065878, May median 0.000000, May active mean -0.016837.
- `no_trade`: all rows flat by construction.

The long-only control remains weak, which preserves short-side asymmetry as a
diagnostic. The no-health ablation has better May breadth and a better median
than the selected health-gated set, and the inverse-health diagnostic is not
dead. That weakens the claim that the health gates are a robust alpha filter;
they mostly reduce participation.

## Best May Diagnostics

Four selected rows tie for the best May return at +0.056746. The summary
representative is `or198-76e752a4e51c7f11`, an ETHUSDT opening-range short
with:

- opening window: 4 completed 15m bars;
- hold: 32 bars;
- session: all;
- state filter: `controlled_downside_extension`;
- target raw signals: 2/day;
- threshold multiplier: 1.30;
- daily cap: 1;
- health gate: `rolling_3_loss_count_le1`.

Pre-May:

- 57 trades over 57 active days;
- 20 active months and eight inactive months;
- four losing active months, all in 2025;
- total net return +0.822889;
- expectancy +0.014437 per trade;
- max drawdown -0.051303;
- Sortino +1.497782;
- best-month share 0.236962;
- 100% cost-stress survival.

May benchmark:

- three trades over three active days;
- total net return +0.056746;
- max drawdown 0.000000;
- no losing May month.

The top-tie rows all remain research diagnostics, not candidates. They still
have four or five pre-May losing months and rely on turning the strategy off
for eight inactive pre-May months.

## Interpretation

WPR106-198 does not confirm the WPR106-197 health-gated repair as
candidate-ready. Behavior deduplication and higher-active selection reduced
duplicate evidence, but the fixed set lost the WPR106-197 aggregate May edge:
the median dropped from +0.004472 in WPR106-197 to 0.000000, negative May rows
rose to 36 out of 100, and the no-health ablation outperformed the selected
health-gated set on May breadth and median.

The controlled-downside ETHUSDT opening-range short remains a useful
research-only diagnostic. It has May-positive top-tie rows, short-side
asymmetry, and cost-stress survival. It is not candidate-ready,
portfolio-ready, or promotion-ready because:

- zero selected rows are strict pre-May rows;
- median selected losing months is five;
- selected rows still rely on inactive months for repair;
- no-health and inverse-health controls weaken the health-gate explanation;
- May transfer is mixed at the selected-set level.

## Artifacts

- `data/research/wpr106_198_opening_range_short_behavior_confirmation/pre_may/source_pool_pre_may_rows.parquet`
- `data/research/wpr106_198_opening_range_short_behavior_confirmation/pre_may/source_pool_pre_may_replay_metrics.parquet`
- `data/research/wpr106_198_opening_range_short_behavior_confirmation/pre_may/source_pool_pre_may_monthly_returns.parquet`
- `data/research/wpr106_198_opening_range_short_behavior_confirmation/pre_may/behavior_deduped_pre_may_metrics.parquet`
- `data/research/wpr106_198_opening_range_short_behavior_confirmation/pre_may/selected_pre_may_rows.parquet`
- `data/research/wpr106_198_opening_range_short_behavior_confirmation/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_198_opening_range_short_behavior_confirmation/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_198_opening_range_short_behavior_confirmation/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_198_opening_range_short_behavior_confirmation/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_198_opening_range_short_behavior_confirmation/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_198_opening_range_short_behavior_confirmation/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_198_opening_range_short_behavior_confirmation/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_198_opening_range_short_behavior_confirmation/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_198_opening_range_short_behavior_confirmation/controls/selected_control_metrics.parquet`
- `data/research/wpr106_198_opening_range_short_behavior_confirmation/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_198_opening_range_short_behavior_confirmation/wpr106_198_opening_range_short_behavior_confirmation_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_198_opening_range_short_behavior_confirmation\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
