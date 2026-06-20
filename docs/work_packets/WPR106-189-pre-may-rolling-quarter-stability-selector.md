# WPR106-189 Pre-May Rolling-Quarter Stability Selector

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the broad 2024-forward research search after WPR106-188 rejected
diversity-capped recent-family portfolios. WPR106-188 still selected many rows
that looked stable in aggregate pre-May metrics but failed May. This packet
tests whether a stricter pre-May rolling-quarter and month-stability selector
can identify any source portfolio whose edge is not concentrated in one or two
profitable windows.

This is an artifact-only research packet, not a candidate-promotion packet.

## Scope

Selection/tuning window:

- 2024-01-01 through 2026-04-30 UTC.

Benchmark-only window:

- May 2026, replayed only after fixed pre-May selection.

Inputs:

- WPR106-188 generated portfolio ranking, monthly returns, source metrics, and
  underlying selected source trade artifacts.

Selector family:

- rolling three-month and six-month return floors;
- calendar-quarter return diagnostics plus a 2026-April stub;
- negative-quarter count, worst-quarter return, latest-quarter behavior, and
  drop-best-month diagnostics;
- source-diversity and dominant-source controls already encoded in WPR106-188
  portfolio descriptors;
- pre-May-only fixed selection, followed by May replay of the fixed rows.

May must not be used for selector thresholds, selector scoring, row inclusion,
daily-cap choice, source inclusion, or tie-breaking. May is benchmark-only
after fixed pre-May selection.

## Allowed Paths

- `docs/work_packets/WPR106-189-pre-may-rolling-quarter-stability-selector.md`
- `docs/stage_reports/STAGE_R106_PRE_MAY_ROLLING_QUARTER_STABILITY_SELECTOR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/**`

## Plan

1. Load WPR106-188 pre-May portfolio ranking and monthly returns.
2. Compute rolling three-month, rolling six-month, quarter/stub, annual, and
   drop-best diagnostics using only 2024-01-01 through 2026-04-30.
3. Select fixed portfolios with pre-May rolling/quarter stability constraints,
   preserving source-diversity caps.
4. Replay selected portfolios on pre-May and May using the WPR106-188 source
   trade accounting and embedded source costs.
5. Write selector diagnostics, selected pre-May, May benchmark, monthly/daily/
   trade artifacts, summary, report, ledger update, and validation notes.

## Research Boundary

All outputs remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_189_pre_may_rolling_quarter_stability_selector\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Closed on 2026-06-12 as a negative research result.

The packet-local runner
`data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/scripts/run_wpr106_189_pre_may_rolling_quarter_stability_selector.py`
loaded the WPR106-188 4,665-row portfolio universe and computed pre-May-only
rolling three-month, rolling six-month, quarter/stub, negative-period,
drop-best-month, and latest-four-month diagnostics.

Pre-May selector diagnostics:

- 4,665 input portfolio rows.
- 4,665 diagnostic rows.
- 162 quarter-strict rows.
- Negative-period distribution: 110 rows with zero negative periods, 2,200
  with one, 1,644 with two, 588 with three, 120 with four, and three with five.

Fixed selected set:

- 100 selected rows.
- 38 `quarter_strict`, 47 `quarter_loose`, 15 `rolling_floor`.
- 38 `exclude_vwap`, 37 `packet_balanced`, 25 `cap_one_vwap`.

Selected pre-May replay:

- 100 positive rows, 0 negative rows, 0 flat rows.
- Median net return: +0.641989.
- Active mean net return: +0.664281.
- Best/worst selected rows: +1.086975 / +0.316491.

May 2026 benchmark replay:

- 6 positive rows, 94 negative rows, 0 flat rows.
- Median net return: -0.026537.
- Active mean net return: -0.027378.
- Best/worst selected rows: +0.001586 / -0.067318.
- `quarter_strict`: 6 positive / 32 negative, median -0.016819.
- `quarter_loose`: 0 positive / 47 negative, median -0.026537.
- `rolling_floor`: 0 positive / 15 negative, median -0.030527.

The fixed selected set is rejected as candidate-ready, portfolio-ready, or
promotion-ready. The stricter pre-May rolling-quarter selector improved the
count of May-positive rows from WPR106-188's three to six, but the best May row
was still only +0.001586 across 18 trades and the selected set remained 94%
negative in the sealed May benchmark.

Artifacts:

- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/pre_may/portfolio_quarter_stability_diagnostics.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/pre_may/portfolio_quarter_period_returns.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/pre_may/selected_pre_may_portfolios.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/wpr106_189_pre_may_rolling_quarter_stability_selector_summary.json`

Validation passed:

```powershell
python -m compileall -q data\research\wpr106_189_pre_may_rolling_quarter_stability_selector\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
