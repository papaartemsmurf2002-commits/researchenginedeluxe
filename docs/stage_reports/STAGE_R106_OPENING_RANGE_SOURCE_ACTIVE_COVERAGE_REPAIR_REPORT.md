# Stage R106 WPR106-201 Opening-Range Source Active-Coverage Repair Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-201 audited the WPR106-197 ETHUSDT opening-range source pocket isolated
by WPR106-200. The question was whether the profitable but sparse
opening-range short behavior could be repaired into a more active,
month-stable research lead without using May 2026 for tuning.

The two WPR106-197 source anchors
`or197-aaf5acc56f96eddc` and `or197-f37732bbc7bd4db6` were preserved as
reference-only rows. They were not used to tune the WPR106-201 selected set.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_201_opening_range_source_active_coverage_repair/scripts/run_wpr106_201_opening_range_source_active_coverage_repair.py`

The runner imports WPR106-197 helpers and reuses WPR106-196/WPR106-170
ETHUSDT opening-range features, fixed-hold labels, costs, overlap blocking,
daily caps, monthly diagnostics, drawdown, Sortino, and cost-stress
accounting. The search grid covers nearby opening windows, holds, sessions,
state filters, target raw signal rates, threshold multipliers, daily caps, and
causal prior-month gates. May 2026 is benchmark-only after fixed pre-May
selection.

Runtime was 251.67 seconds. CUDA was not used and no speedup claim was made.
The initial broader grid was stopped after a timeout before any Parquet
artifact was written; the completed final run is the bounded 21,600-row grid.

## Search Results

WPR106-201 evaluated 21,600 pre-May rows:

- 17,472 positive pre-May rows.
- 3,535 annual-target rows.
- 3,496 rows with at least 24 active pre-May months.
- 1,030 loose rows.
- Zero strict rows.

No positive row combined at least 24 active pre-May months with the annual
loss-month target. Only two selected rows reached at least 24 active months
and five or fewer losing months, and both benchmarked slightly negative in
May.

The fixed selected set contains 100 rows:

- 99 `active_repair` rows.
- 1 `source_pocket_anchor` row.
- 100/100 positive pre-May.
- Median pre-May net return: +0.714290.
- Median active months: 22.
- Median inactive months: 6.
- Median losing months: 6.
- Zero strict rows.
- One annual-target row.

The best pre-May row is `or201-1f16731b9eeb37f1`, an ETHUSDT US-session
opening-range short with an 8-bar opening window, 32-bar hold, bearish-trend
state, no health gate, target raw rate 4/day, threshold multiplier 1.15, and
daily cap 1. It records +1.051022 pre-May over 139 trades, all 28 pre-May
months active, seven losing months, max drawdown -0.117441, 100% cost-stress
survival, and +0.007628 in May over six trades. It fails the target stability
profile because losing months are 3/3/1 across 2024/2025/2026.

The strongest active-coverage repair near the original controlled-downside
source is `or201-ce81f63d6911db8b`, equivalent to WPR106-197
`or197-0281af63a2f4d05d` with no health gate. It records +0.899985 pre-May
over 106 trades, all 28 pre-May months active, six losing months, max
drawdown -0.073481, and 100% cost-stress survival, but benchmarks -0.003969
in May over three trades.

The two rows with at least 24 active pre-May months and five or fewer losing
months are:

- `or201-d092f14fcee5eeaf`: +0.916713 pre-May, 25 active months, four losing
  months, max drawdown -0.073481, May -0.003969 over three trades.
- `or201-aca1febd4c67ef45`: +0.879934 pre-May, 24 active months, five losing
  months, max drawdown -0.073481, May -0.003969 over three trades.

## May Benchmark

The selected-set May benchmark is mixed:

- 75 active rows and 25 flat/no-trade rows.
- 43 positive rows and 32 negative rows.
- Median May net return: 0.000000.
- Active mean May net return: +0.000878.
- Best May row: +0.023197.
- Worst May row: -0.026205.

The best May row is `or201-37e8fa179f8ba905`, with +0.538902 pre-May over
104 trades, 22 active months, seven losing months, and +0.023197 in May over
four trades. It does not meet the month-stability target.

## Reference Anchors

The two predeclared WPR106-197 reference anchors remain profitable but sparse:

- Median pre-May return: +0.958549.
- Median active months: 19.
- Median inactive months: 9.
- Median losing months: 3.5.
- Both annual-target rows.
- Median May return: +0.050189.

This confirms the WPR106-200 interpretation: the sparse source pocket is real
enough to remain a diagnostic, but its stability depends on inactivity rather
than a repaired active monthly profile.

## Controls

Selected source controls produced 668 rows:

- 579/668 controls are positive pre-May.
- 242/668 controls are May-positive.
- Median pre-May control return: +0.536473.
- Median May control return: 0.000000.

The no-state-filter controls have the best May median (+0.007628), but they
are controls over already selected rows, not independent candidate evidence.
Long-side controls have negative median pre-May return (-0.110904), preserving
the short-side asymmetry as a diagnostic.

## Interpretation

WPR106-201 rejects the opening-range source active-coverage repair as
candidate-ready, portfolio-ready, or promotion-ready. The repair can increase
activity to all pre-May months and keep costs/drawdown tolerable, but it gives
up the desired annual loss-month stability and does not produce a convincing
May benchmark. The original WPR106-197 source anchors remain stronger on
annual loss counts and May, but only by staying sparse with nine inactive
pre-May months.

The useful follow-up is not to continue defending the sparse source row. It is
to move the broad 2024-forward search to other families or use opening-range
short behavior only as a research-only component with predeclared active
coverage and stability gates.

No WPR106-201 row is candidate-ready, portfolio-ready, or promotion-ready.

## Artifacts

- `data/research/wpr106_201_opening_range_source_active_coverage_repair/pre_may/opening_range_source_active_coverage_pre_may_ranking.parquet`
- `data/research/wpr106_201_opening_range_source_active_coverage_repair/pre_may/opening_range_source_active_coverage_pre_may_top5000.csv`
- `data/research/wpr106_201_opening_range_source_active_coverage_repair/pre_may/opening_range_source_active_coverage_pre_may_monthly_returns.parquet`
- `data/research/wpr106_201_opening_range_source_active_coverage_repair/pre_may/selected_pre_may_rows.parquet`
- `data/research/wpr106_201_opening_range_source_active_coverage_repair/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_201_opening_range_source_active_coverage_repair/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_201_opening_range_source_active_coverage_repair/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_201_opening_range_source_active_coverage_repair/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_201_opening_range_source_active_coverage_repair/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_201_opening_range_source_active_coverage_repair/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_201_opening_range_source_active_coverage_repair/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_201_opening_range_source_active_coverage_repair/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_201_opening_range_source_active_coverage_repair/may_benchmark/wpr197_reference_anchor_may_benchmark_metrics.parquet`
- `data/research/wpr106_201_opening_range_source_active_coverage_repair/controls/selected_source_control_metrics.parquet`
- `data/research/wpr106_201_opening_range_source_active_coverage_repair/controls/wpr197_reference_anchor_pre_may_metrics.parquet`
- `data/research/wpr106_201_opening_range_source_active_coverage_repair/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_201_opening_range_source_active_coverage_repair/wpr106_201_opening_range_source_active_coverage_repair_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_201_opening_range_source_active_coverage_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
