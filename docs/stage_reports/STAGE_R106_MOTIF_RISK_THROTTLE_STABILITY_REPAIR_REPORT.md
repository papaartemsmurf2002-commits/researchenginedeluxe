# Stage R106 WPR106-202 Motif Risk-Throttle Stability Repair Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-202 tested whether the WPR106-192 causal state/motif lookup family
could be repaired with accepted-trade risk and activity throttles instead of
exit changes. WPR106-192 found active May transfer, especially in ETHUSDT
`trend_pullback_clock`, but the pre-May rows had too many losing months and
large drawdowns. WPR106-193 showed that simple stop/target path exits did not
repair that pocket.

This packet keeps WPR106-192 selected source entries fixed. It can only drop
accepted trades using pre-entry motif quality fields, side filters, source
daily-cap reductions, and prior-month health gates.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_202_motif_risk_throttle_stability_repair/scripts/run_wpr106_202_motif_risk_throttle_stability_repair.py`

The runner reads WPR106-192 selected pre-May and May trade artifacts, computes
source-local pre-May motif-quality thresholds, evaluates accepted-trade overlay
variants, ranks only on 2024-01-01 through 2026-04-30 evidence, and benchmarks
May 2026 only after the selected overlay set is fixed.

Overlay dimensions:

- side filter: all, long, short;
- quality filter: none, motif mean q50/q75, motif good-rate q50,
  mean-and-good q50, motif side-spread q50;
- effective daily cap: 1, 2, 3, or 5, never above the source daily cap;
- causal monthly health gate: none, previous-month positive, rolling 3/6 month
  positive or loss-count gates.

Runtime was 578.25 seconds. CUDA was not used and no speedup claim was made.

## Results

WPR106-202 evaluated 17,766 pre-May overlay rows:

- 10,089 positive pre-May rows.
- 4,812 annual-target rows.
- 32 loose rows.
- Zero strict rows.
- Zero positive rows with at least 20 active months and five or fewer losing
  months.
- Zero positive annual-target rows with at least 20 active months.

The fixed selected set contains 100 rows:

- All 100 are `positive_recent_throttle` rows.
- All 100 are ETHUSDT `trend_pullback_clock` rows.
- All 100 are positive pre-May.
- Median pre-May net return: +0.766617.
- Median active months: 28.
- Median losing months: 10.
- Median inactive months: 0.
- Zero strict rows.
- Zero annual-target rows.

This improves return and activity relative to the WPR106-192 source baseline,
but not the requested month-to-month stability. The WPR106-192 selected source
baseline had median pre-May return +0.205355, median active months 27, and
median losing months 13.

## May Benchmark

May transfer improves strongly versus WPR106-192:

- 100 active selected rows.
- 98 positive rows and two negative rows.
- Median May net return: +0.027644.
- Active mean May net return: +0.018009.
- Best May row: +0.039212.
- Worst May row: -0.008458.

The WPR106-192 selected source baseline had 45 positive and 29 negative May
rows with median May +0.008759. WPR106-202 therefore improves May transfer,
but this does not rescue the family because the pre-May annual/monthly profile
still fails.

## Best Rows

The best pre-May row is `motif202-452e840bf09d2d48`, sourced from
`motif192-35ec7a82a44aace0`. It is ETHUSDT `trend_pullback_clock`, US session,
long source side, 32-bar hold, motif mean q50 quality filter, and effective
daily cap 1. It records +0.806192 pre-May over 263 trades, all 28 pre-May
months active, 10 losing months, max drawdown -0.353936, and 100%
cost-stress survival. It is not stable enough.

The best stability and best May row are the same overlay:
`motif202-00860ffdbf2eb058`, sourced from WPR106-192
`motif192-e04007619d5902f3`. It is ETHUSDT `trend_pullback_clock`, US session,
long-only accepted-trade overlay, motif mean q75 quality filter, and effective
daily cap 1. It records +0.720677 pre-May over 103 trades, 23 active months,
seven losing months, max drawdown -0.067553, 100% cost-stress survival, and
+0.039212 in May over five trades. It is a useful diagnostic, but it misses
the requested active annual loss-month profile: four losing months in 2024,
two in 2025, and one in 2026 Jan-Apr.

Only six positive rows reached at least 22 active months and seven or fewer
losing months. None reached five or fewer losing months with at least 20 active
months.

## Interpretation

WPR106-202 rejects motif risk throttles as candidate-ready, portfolio-ready,
or promotion-ready. Accepted-trade throttles improve May transfer and reduce
some drawdowns, but the family still cannot produce the requested
month-to-month stability over 2024-forward pre-May evidence. The stronger May
benchmark is not enough because it arrives after pre-May selection and cannot
override the pre-May stability failure.

The useful diagnostic is narrow: ETHUSDT US-session `trend_pullback_clock`
with long-only high-quality motif throttles remains a research-only component
candidate for future ensemble or source-logic experiments, but not a standalone
lead.

No WPR106-202 row is candidate-ready, portfolio-ready, or promotion-ready.

## Artifacts

- `data/research/wpr106_202_motif_risk_throttle_stability_repair/pre_may/motif_risk_throttle_pre_may_ranking.parquet`
- `data/research/wpr106_202_motif_risk_throttle_stability_repair/pre_may/motif_risk_throttle_pre_may_top5000.csv`
- `data/research/wpr106_202_motif_risk_throttle_stability_repair/pre_may/motif_risk_throttle_pre_may_monthly_returns.parquet`
- `data/research/wpr106_202_motif_risk_throttle_stability_repair/pre_may/selected_pre_may_overlay_rows.parquet`
- `data/research/wpr106_202_motif_risk_throttle_stability_repair/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_202_motif_risk_throttle_stability_repair/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_202_motif_risk_throttle_stability_repair/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_202_motif_risk_throttle_stability_repair/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_202_motif_risk_throttle_stability_repair/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_202_motif_risk_throttle_stability_repair/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_202_motif_risk_throttle_stability_repair/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_202_motif_risk_throttle_stability_repair/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_202_motif_risk_throttle_stability_repair/controls/wpr106_192_source_baseline_comparison.parquet`
- `data/research/wpr106_202_motif_risk_throttle_stability_repair/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_202_motif_risk_throttle_stability_repair/wpr106_202_motif_risk_throttle_stability_repair_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_202_motif_risk_throttle_stability_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
