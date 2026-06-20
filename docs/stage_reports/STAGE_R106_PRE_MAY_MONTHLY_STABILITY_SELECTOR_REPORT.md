# Stage R106 Pre-May Monthly Stability Selector Report

Date: 2026-06-12
Work packet: WPR106-178-pre-may-monthly-stability-selector
Status: stability selector completed, no May-confirmed lead

## Scope

WPR106-178 tests whether a monthly-stability-first selector can improve
transfer from the recent WPR106-176 and WPR106-177 search spaces. The objective
is to prioritize the user-requested profile: stable month-to-month behavior,
low annual losing-month counts, active trade rates, cost survival, and reduced
best-month dependence.

Selection uses only 2024-01-01 through 2026-04-30 metrics and monthly rows.
May 2026 and June 1-11 2026 are fixed replay benchmarks after selection.

This packet is research-only and observe-only. It writes no candidate pack,
paper/live artifact, live configuration, sizing change, order path, CUDA
speedup claim, or promotion claim.

## Method

Inputs:

- WPR106-176 full pre-May ranking and monthly artifacts;
- WPR106-177 full pre-May ranking and monthly artifacts;
- WPR106-96 BTCUSDT/ETHUSDT context through May 2026 as rolling-feature
  warmup;
- WPR106-168 BTCUSDT/ETHUSDT June 1-11 2026 15m bars and 1m aggTrade flow
  context for fresh non-May replay.

The selector computes pre-May-only diagnostics:

- annual losing-month counts;
- active-month coverage;
- active 1-5 trades/day filter;
- cost-stress survival;
- best-month share;
- return after dropping the best three months;
- rolling 3-month and 6-month return minima;
- behavior/path duplicate groups after selected pre-May replay.

The runner loads WPR106-176 and WPR106-177 helper code only for fixed replay.
No May or June row is used for scoring, ranking, or selection.

Runtime was 76.6 seconds. CUDA was not used and no speedup is claimed.

## Selector Results

| Metric | Value |
| --- | ---: |
| Universe rows | 75,360 |
| Stability-candidate rows | 2,016 |
| Selected rows | 100 |
| WPR106-176 selected rows | 49 |
| WPR106-177 selected rows | 51 |
| Strict selected rows | 5 |
| Stability selected rows | 95 |
| Unique selected pre-May path hashes | 68 |
| Largest duplicate path group | 4 |

Selected rows are more stable than the raw score-ranked selections, but still
do not reach the target annual profile often enough. Only five selected rows
pass annual loss caps of at most 2 losing months in 2024, at most 2 in 2025,
and at most 1 in 2026 Jan-Apr. All five are WPR106-176 ETHUSDT
`vol_breakout_follow` rows from the already-rejected cluster.

## Benchmarks

| Metric | Pre-May Replay | May 2026 | June 1-11 2026 |
| --- | ---: | ---: | ---: |
| Rows | 100 | 100 | 100 |
| Active rows | 100 | 69 | 100 |
| Positive rows | 97 | 24 | 69 |
| Negative rows | 3 | 45 | 31 |
| Flat rows | 0 | 31 | 0 |
| Median return | +0.967411 | 0.000000 | +0.019182 |
| Active mean return | +0.958284 | -0.015527 | +0.009868 |
| Best return | +1.938118 | +0.034386 | +0.069733 |
| Worst return | -1.024716 | -0.084557 | -0.085387 |

May remains the rejection point. The selector improves June versus WPR106-177,
but this is not enough because May is benchmark-only and negative on active
rows.

Selected benchmark by source/template:

| Source | Symbol | Template | Rows | May pos/neg/flat | June pos/neg | May median | June median |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| WPR106-176 | BTCUSDT | `vol_breakout_follow` | 18 | 10/5/3 | 14/4 | +0.009594 | +0.007145 |
| WPR106-177 | ETHUSDT | `cross_relative_reversion` | 18 | 6/0/12 | 12/6 | 0.000000 | +0.000897 |
| WPR106-177 | BTCUSDT | `flow_absorption_fade` | 10 | 3/7/0 | 4/6 | -0.070753 | -0.014950 |
| WPR106-177 | ETHUSDT | `flow_absorption_fade` | 9 | 3/6/0 | 0/9 | -0.008116 | -0.048296 |
| WPR106-177 | ETHUSDT | `range_zscore_flow_revert` | 11 | 1/7/3 | 8/3 | -0.015358 | +0.039843 |
| WPR106-176 | ETHUSDT | `vol_breakout_follow` | 18 | 0/13/5 | 17/1 | -0.008116 | +0.029682 |
| WPR106-176 | ETHUSDT | `flow_burst_follow` | 11 | 0/3/8 | 11/0 | 0.000000 | +0.055337 |

Best May row:

- candidate: `switch-552a994db993efe5`;
- source: WPR106-176;
- symbol/template: BTCUSDT `vol_breakout_follow`;
- policy: `direct_flow_confirm_inverse_contra_skip`;
- May trades: 10;
- May return: +0.034386;
- June return: +0.023633;
- pre-May return: +0.812237.

Best June row:

- candidate: `switch-a2f3af915d39b91f`;
- source: WPR106-176;
- symbol/template: ETHUSDT `vol_breakout_follow`;
- policy: `inverse_all`;
- May return: -0.061778;
- June trades: 32;
- June return: +0.069733;
- pre-May return: +1.899726.

Annual-loss-compliant selected subset:

| Metric | Value |
| --- | ---: |
| Rows | 5 |
| May mean return | -0.019544 |
| May-positive rows | 0 |
| June mean return | +0.034830 |
| Source/template | WPR106-176 ETHUSDT `vol_breakout_follow` |

## Decision

WPR106-178 rejects the pre-May monthly stability selector as candidate-ready,
portfolio-ready, or promotion-ready evidence.

The selector made useful progress by showing that stability-weighted scoring
can improve June and select a more conservative pre-May set. However, it fails
the required benchmark behavior:

- May active mean is negative.
- May has more negative than positive selected rows.
- The annual-loss-compliant subset is tiny, all from the already-rejected
  ETHUSDT volatility-breakout cluster, and still May-negative.
- Selected behavior remains duplicate-heavy with 68 unique path hashes from
  100 selected rows.

Useful diagnostics to preserve:

- BTCUSDT WPR106-176 `vol_breakout_follow` with
  `direct_flow_confirm_inverse_contra_skip` is the only selected group with a
  positive May median and positive June median.
- ETHUSDT WPR106-177 `cross_relative_reversion` is flat/positive in May but
  mixed in June.

Neither diagnostic supports a candidate claim.

## Artifacts

- Runner:
  `data/research/wpr106_178_pre_may_monthly_stability_selector/scripts/run_wpr106_178_pre_may_monthly_stability_selector.py`
- Summary:
  `data/research/wpr106_178_pre_may_monthly_stability_selector/wpr106_178_pre_may_monthly_stability_selector_summary.json`
- Scored universe:
  `data/research/wpr106_178_pre_may_monthly_stability_selector/selector/stability_scored_universe.parquet`
- Selected rows:
  `data/research/wpr106_178_pre_may_monthly_stability_selector/selector/selected_stability_rows.parquet`
- Selected pre-May, May, and June metrics:
  `data/research/wpr106_178_pre_may_monthly_stability_selector/selected_replay/selected_pre_may_metrics.parquet`,
  `selected_may_metrics.parquet`, and `selected_june_metrics.parquet`
- Selected pre-May/May/June comparison:
  `data/research/wpr106_178_pre_may_monthly_stability_selector/selected_replay/selected_pre_may_may_june_comparison.parquet`
- Selected trade ledgers:
  `data/research/wpr106_178_pre_may_monthly_stability_selector/selected_replay/selected_pre_may_trades.parquet`,
  `selected_may_trades.parquet`, and `selected_june_trades.parquet`

## Validation

Passed:

- `python -m compileall -q data\research\wpr106_178_pre_may_monthly_stability_selector\scripts`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`

Contract result: 460 passed.
