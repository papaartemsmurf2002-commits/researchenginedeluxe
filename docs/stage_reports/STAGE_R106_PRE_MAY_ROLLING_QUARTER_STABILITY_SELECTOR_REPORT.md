# Stage R106 WPR106-189 Pre-May Rolling-Quarter Stability Selector Report

Status: closed
Date: 2026-06-12
Owner: Codex Research Agent

## Scope

WPR106-189 continued the broad 2024-forward strategy search after WPR106-188
rejected diversity-capped recent-family portfolios. It tested whether a
stricter pre-May rolling-quarter and month-stability selector could identify
portfolios whose edge was not concentrated in one or two profitable windows.

All selector diagnostics, thresholds, scoring, row inclusion, and tie-breaking
used only 2024-01-01 through 2026-04-30 UTC. May 2026 was benchmark-only after
fixed pre-May selection.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/scripts/run_wpr106_189_pre_may_rolling_quarter_stability_selector.py`

The runner imports the WPR106-188 replay/accounting functions, preserves
embedded source costs and same-symbol overlap handling, and writes new
WPR106-189 selector candidate IDs while retaining the original WPR106-188
portfolio candidate ID for lineage. It computes rolling three-month and
six-month floors, calendar-quarter returns, a 2026-April stub, negative-period
counts, worst-period return, best-period concentration, drop-best-month
returns, and latest-four-month behavior from pre-May monthly returns only.

Runtime was 21.76 seconds. CUDA was not used and no speedup claim was made.

## Results

Pre-May selector diagnostics:

- 4,665 input portfolio rows.
- 4,665 diagnostic rows.
- 162 quarter-strict rows.
- Negative-period distribution: 110 rows with zero negative periods, 2,200
  with one, 1,644 with two, 588 with three, 120 with four, and three with five.

Quarter-strict rows by WPR106-188 control universe:

- `exclude_vwap`: 52 rows, median +1.027224 pre-May, median worst period
  -0.024746.
- `cap_one_vwap`: 37 rows, median +0.867247 pre-May, median worst period
  +0.023340.
- `packet_balanced`: 73 rows, median +0.832003 pre-May, median worst period
  +0.006912.

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

May by selection tier:

- `quarter_strict`: 6 positive / 32 negative, median -0.016819, mean -0.020328.
- `quarter_loose`: 0 positive / 47 negative, median -0.026537, mean -0.029188.
- `rolling_floor`: 0 positive / 15 negative, median -0.030527, mean -0.039569.

May by WPR106-188 control universe:

- `exclude_vwap`: 0 positive / 38 negative, median -0.028729, mean -0.034211.
- `cap_one_vwap`: 0 positive / 25 negative, median -0.025024, mean -0.028290.
- `packet_balanced`: 6 positive / 31 negative, median -0.026663, mean -0.019744.

The best May row was `rqsel189-af299d51e831bfa1`, a quarter-strict
packet-balanced drawdown-complement portfolio using WPR106-180, WPR106-183,
and WPR106-185 sources. It had zero negative pre-May periods, worst pre-May
period +0.013659, rolling six-month minimum +0.014600, latest-four-month
return +0.202349, and +0.684899 pre-May over 429 trades, but only +0.001586 in
May over 18 trades.

## Interpretation

Pre-May rolling-quarter stability improves diagnostics but does not produce a
May-transferable portfolio lead. The strict selector raised the May-positive
count from WPR106-188's three selected rows to six, but those positives are
economically negligible and all non-packet-balanced controls still have zero
May-positive selected rows.

WPR106-189 therefore rejects the pre-May rolling-quarter stability selector as
candidate-ready, portfolio-ready, or promotion-ready. The result further
supports moving away from selectors over the WPR106-180 through WPR106-186
recent-family portfolio universe and toward genuinely different entry/exit
families or model features.

## Artifacts

- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/pre_may/portfolio_quarter_stability_diagnostics.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/pre_may/portfolio_quarter_stability_diagnostics.csv`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/pre_may/portfolio_quarter_period_returns.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/pre_may/selected_pre_may_portfolios.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/pre_may/selected_pre_may_portfolios.csv`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/pre_may/selected_pre_may_replay_metrics.csv`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/may_benchmark/selected_may_benchmark_metrics.csv`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/selected_pre_may_may_comparison.csv`
- `data/research/wpr106_189_pre_may_rolling_quarter_stability_selector/wpr106_189_pre_may_rolling_quarter_stability_selector_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_189_pre_may_rolling_quarter_stability_selector\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
