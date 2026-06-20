# Stage R106 Direct Pocket Pseudo-Holdout Controls Report

Date: 2026-06-12
Work packet: WPR106-165-direct-pocket-pseudo-holdout-controls
Status: rejected as candidate-ready, portfolio-ready, and promotion-ready
evidence; WPR106-146 retained as a research-only follow-up clue

## Scope

WPR106-165 ran a direct control audit on the two narrow pockets that remained
interesting after repeated broad May-blind selectors:

- WPR106-146 cross-symbol relative-strength trade-veto;
- WPR106-128 anchored VWAP flow-impulse.

The packet is intentionally fail-closed. These pockets were already noticed
through prior May benchmark summaries, so May 2026 is not a fresh independent
discovery holdout here. The audit asks only whether the fixed target pockets
looked stable under pre-May pseudo-holdouts, matched controls, and simple
pre-May-only portfolio construction before comparing them to May as a benchmark.

All row scoring, pseudo-holdout diagnostics, target selection, control
matching, portfolio construction, and portfolio ranking used only 2024-01-01
through 2026-04-30. May 2026 was used only after rows, controls, and portfolios
were fixed.

The packet is research-only and observe-only. It writes no candidate pack, no
paper/live artifact, no live configuration, no sizing change, no order path,
and no promotion claim.

## Inputs

The runner rebuilt the WPR106-157 broad artifact universe and reused WPR106-163
daily/monthly diagnostics:

- Included packet directories: 43.
- Loaded metric rows: 2,925.
- Loaded pre-May trade rows: 591,571.
- Loaded May benchmark trade rows: 21,216.
- Behavior-deduplicated source rows: 1,915.
- Target source rows: 47.

Fixed target rows:

- WPR106-128 anchored VWAP flow-impulse: 30 rows.
- WPR106-146 relative-strength trade-veto: 17 rows.

The runner matched one non-target control for each selected target row using
symbol, trade-count scale, total return, validation return, adverse-month/day
profile, and pseudo-holdout profile.

## Method

The runner computed pre-May row metrics, monthly returns, daily returns,
adverse-month and adverse-day diagnostics, annual losing-month counts, active
rates, drawdown, best-month concentration, and drop-best-month robustness.

Each pre-May month was treated as a pseudo-holdout. The target rows were scored
on positive/negative withheld months, worst and median withheld month,
validation return, adverse-period behavior, cost stress, concentration, and
trade activity. Matched controls and equal-sleeve portfolios were then frozen
from pre-May evidence before May was evaluated.

All written rows and portfolios carry `research_only: true`, `observe_only:
true`, `promotion_ready: false`, and `may_2026_used_for_selection: false`.

## Pre-May Target Diagnostics

WPR106-146 was the stronger pre-May pocket:

- 17 selected rows.
- Pseudo tiers: 15 strict, 2 robust.
- Median total net return: +0.944238.
- Median 2026 Jan-Apr validation return: +0.121175.
- Median adverse-month return: +0.015880.
- Median adverse-day return: -0.281538.
- Median drop-best-three-month return: +0.515259.
- Median pseudo-holdout positive months: 21.
- Median pseudo-holdout negative months: 5.
- Median pseudo-holdout month return: +0.030888.
- Median worst pseudo-holdout month: -0.065446.
- Median trades per active day: 1.000000.

WPR106-128 looked positive pre-May but weaker:

- 30 selected rows.
- Pseudo tiers: 16 positive, 14 robust.
- Median total net return: +0.833973.
- Median 2026 Jan-Apr validation return: +0.124785.
- Median adverse-month return: +0.029412.
- Median adverse-day return: -0.353450.
- Median drop-best-three-month return: +0.378766.
- Median pseudo-holdout positive months: 20.
- Median pseudo-holdout negative months: 8.
- Median pseudo-holdout month return: +0.026289.
- Median worst pseudo-holdout month: -0.076687.
- Median trades per active day: 1.114650.

## May 2026 Row Benchmark

May split the target pockets sharply:

| Group | Rows | Positive | Negative | Flat | Best | Worst | Median | Mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Target pockets | 47 | 30 | 16 | 1 | +0.067949 | -0.107429 | +0.006251 | +0.007892 |
| Matched controls | 47 | 7 | 40 | 0 | +0.049556 | -0.093512 | -0.022573 | -0.023592 |

Target-pocket detail:

| Target pocket | Rows | Positive | Negative | Flat | Best | Worst | Median | Mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| WPR106-146 relative-strength trade-veto | 17 | 17 | 0 | 0 | +0.067949 | +0.015398 | +0.030569 | +0.037985 |
| WPR106-128 anchored VWAP flow-impulse | 30 | 13 | 16 | 1 | +0.027293 | -0.107429 | -0.002686 | -0.009161 |

Matched-control detail:

| Matched target pocket | Rows | Positive | Negative | Flat | Best | Worst | Median | Mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Controls matched to WPR106-146 | 17 | 1 | 16 | 0 | +0.004096 | -0.060785 | -0.017301 | -0.023275 |
| Controls matched to WPR106-128 | 30 | 6 | 24 | 0 | +0.049556 | -0.093512 | -0.024392 | -0.023772 |

The direct row audit rejects WPR106-128 as a direct May benchmark lead. It
preserves WPR106-146 as the strongest post-hoc research-only pocket found so
far, but not as candidate-ready evidence.

## May 2026 Portfolio Benchmark

The runner generated 872 candidate portfolios and selected 52 fixed portfolios
from pre-May evidence: 28 target-pocket portfolios and 24 matched-control
portfolios.

Target-pocket portfolio pre-May medians:

- Total net return: +1.147168.
- 2026 Jan-Apr validation return: +0.194533.
- Drop-best-three-month return: +0.736761.
- Adverse-month return: +0.095545.
- Losing months: 6.
- Overlap-day share: 0.314819.
- Mean pair absolute correlation: 0.539166.
- Sleeve-average trades per active day: 0.649125.

Matched-control portfolio pre-May medians:

- Total net return: +0.975271.
- 2026 Jan-Apr validation return: +0.180095.
- Drop-best-three-month return: +0.692123.
- Adverse-month return: +0.097385.
- Losing months: 1.
- Overlap-day share: 0.812874.
- Mean pair absolute correlation: 0.278335.
- Sleeve-average trades per active day: 0.401478.

May portfolio benchmark:

| Group | Portfolios | Positive | Negative | Best | Worst | Median | Mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Target-pocket portfolios | 28 | 28 | 0 | +0.063858 | +0.007776 | +0.023694 | +0.024733 |
| Matched-control portfolios | 24 | 0 | 24 | -0.002688 | -0.039439 | -0.030822 | -0.026689 |

These portfolios are useful as a control finding but not as a promotion path:
the target pocket set was motivated by prior May observations, WPR106-128 was
weak at row level, and the positive target portfolios require fresh non-May
testing, ablations, side/opposite controls, direct strategy reruns, and a
candidate-gate path before they can be trusted.

## Decision

WPR106-165 rejects direct pocket pseudo-holdout controls as candidate-ready,
portfolio-ready, or promotion-ready evidence.

The result narrows the next research steps:

- WPR106-146 cross-symbol relative-strength trade-veto is the strongest
  research-only follow-up clue from the broad 2024-forward search so far. Its
  pre-May pseudo-holdout profile is materially better than controls and its May
  benchmark is uniformly positive at row level.
- WPR106-128 anchored VWAP flow-impulse is rejected by direct controls because
  its May row median and mean were negative despite positive-looking pre-May
  metrics.
- The WPR106-146 clue should be retested only through fresh non-May evidence:
  direct strategy rerun, causal ablations, no-veto/opposite-side controls,
  alternate post-April holdouts where available, cost/overlap stress, and
  repeatable manifest evidence.

No candidate pack, paper/live artifact, order path, sizing change, runtime-mode
change, live config write, CUDA speedup claim, or promotion claim exists.

## Artifacts

- Runner:
  `data/research/wpr106_165_direct_pocket_pseudo_holdout_controls/scripts/run_wpr106_165_direct_pocket_pseudo_holdout_controls.py`
- Summary:
  `data/research/wpr106_165_direct_pocket_pseudo_holdout_controls/wpr106_165_direct_pocket_pseudo_holdout_controls_summary.json`
- Target pre-May ranking:
  `data/research/wpr106_165_direct_pocket_pseudo_holdout_controls/pre_may/target_pocket_pre_may_ranking.parquet`
- Selected target rows:
  `data/research/wpr106_165_direct_pocket_pseudo_holdout_controls/pre_may/selected_pre_may_target_rows.parquet`
- Matched controls:
  `data/research/wpr106_165_direct_pocket_pseudo_holdout_controls/pre_may/matched_control_rows.parquet`
- May row benchmark:
  `data/research/wpr106_165_direct_pocket_pseudo_holdout_controls/may_benchmark/target_and_control_may_metrics.parquet`
- Selected pre-May portfolios:
  `data/research/wpr106_165_direct_pocket_pseudo_holdout_controls/pre_may/selected_target_and_control_pre_may_portfolios.parquet`
- May portfolio benchmark:
  `data/research/wpr106_165_direct_pocket_pseudo_holdout_controls/may_benchmark/target_and_control_may_portfolio_metrics.parquet`

## Validation

Passed:

- `python -m compileall -q data/research/wpr106_165_direct_pocket_pseudo_holdout_controls/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

Contract result: 460 passed.
