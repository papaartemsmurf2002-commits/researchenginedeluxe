# Stage R106 WPR106-194 Intrabar Flow Burst Profile Search Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-194 continued the broad 2024-forward search after WPR106-193 rejected
path-managed exits over WPR106-192 motif entries. It tested a fresh order-flow
style source family using 1m aggTrade-flow profiles inside completed 15m bars.

All feature construction, threshold calibration, hold/session/side/daily-cap
choice, row ranking, and selected-row inclusion used only 2024-01-01 through
2026-04-30 UTC. May 2026 was replayed only after fixed pre-May selection.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_194_intrabar_flow_burst_profile_search/scripts/run_wpr106_194_intrabar_flow_burst_profile_search.py`

The runner imports WPR106-170 helpers for WPR106-96 BTCUSDT/ETHUSDT context,
future fixed-hold labels, period masks, embedded costs, overlap blocking,
monthly diagnostics, annual losing-month checks, drawdown, Sortino, and
cost-stress accounting.

It reads the WPR106-96 1m aggTrade proxy files and builds completed 15m
profiles from the prior fifteen 1m buckets:

- early/mid/late buy-sell quote imbalance;
- late-vs-early and late-vs-mid flow acceleration;
- late quote-volume concentration;
- total quote/trade-count burst z-scores;
- signed late-flow pressure.

Those flow profile features are combined with completed-bar return, wick,
trend, volatility, and cross-symbol residual features into five templates:

- `late_flow_follow`;
- `late_flow_exhaustion_fade`;
- `absorption_reversal`;
- `flow_acceleration_reversal`;
- `cross_symbol_flow_divergence`.

The bounded grid evaluates both symbols, 4/8/16/32-bar holds, all/Asia/EU/US
sessions, 1/3/5 target raw signals per day, both/long/short side modes, and
daily caps of 1/3/5. Runtime was 78.14 seconds. CUDA was not used and no
speedup claim was made.

## Results

Pre-May screen:

- 4,320 evaluated rows.
- 280 positive pre-May rows.
- 0 annual-target rows.
- 0 loose rows.
- 0 strict rows.

Pre-May by symbol:

- BTCUSDT: 2,160 rows, 93 positive, 0 annual-target, best +0.232787, median
  -0.409958.
- ETHUSDT: 2,160 rows, 187 positive, 0 annual-target, best +0.821519, median
  -0.450536.

Best pre-May template pockets:

- ETHUSDT `late_flow_follow`: best +0.821519, but selected May was mostly
  negative.
- ETHUSDT `flow_acceleration_reversal`: best +0.543561, but May selected rows
  were all negative.
- ETHUSDT `late_flow_exhaustion_fade`: best +0.249145 and the strongest May
  pocket, but still excessive pre-May losing months.

Fixed selected set:

- 100 selected rows.
- All 100 are `positive_recent_stability` fallback rows.
- 89 ETHUSDT rows and 11 BTCUSDT rows.
- Template mix: 53 `late_flow_follow`, 24 `cross_symbol_flow_divergence`,
  14 `late_flow_exhaustion_fade`, and 9 `flow_acceleration_reversal`.

Selected pre-May replay:

- 100 positive rows, 0 negative rows, 0 flat rows.
- Median net return: +0.184677.
- Active mean net return: +0.233582.
- Best/worst selected rows: +0.821519 / +0.050271.

May 2026 benchmark replay:

- 100 active rows.
- 22 positive rows and 78 negative rows.
- Median net return: -0.010404.
- Active mean net return: -0.008656.
- Best/worst selected rows: +0.078131 / -0.049117.

May by selected symbol/template:

- ETHUSDT `late_flow_exhaustion_fade`: 12 rows, 9 positive and 3 negative,
  May median +0.048973, best +0.078131.
- BTCUSDT `late_flow_exhaustion_fade`: 2 rows, both positive, May median
  +0.014357.
- ETHUSDT `cross_symbol_flow_divergence`: 24 rows, 5 positive and 19 negative,
  May median -0.003469.
- ETHUSDT `late_flow_follow`: 47 rows, 6 positive and 41 negative, May median
  -0.011809.
- ETHUSDT `flow_acceleration_reversal`: 6 rows, all negative, May median
  -0.026648.

The best May row was `flowburst194-9285cca562cc687e`: ETHUSDT,
`late_flow_exhaustion_fade`, 32-bar hold, EU session, both-sided, daily cap 1.
It had +0.249145 pre-May over 565 trades, 28 active months, and +0.078131 in
May over 18 trades. It is not a candidate lead because it had 14 pre-May losing
months, seven losing months in 2024, five in 2025, two in 2026 Jan-Apr,
negative median trade return, max drawdown -0.465964, and only 50% cost-stress
survival.

## Interpretation

WPR106-194 is rejected as candidate-ready, portfolio-ready, or
promotion-ready. The order-flow style 1m intrabar profile family produced
active entries and some positive May pockets, but it did not produce any
annual-target, loose, or strict pre-May rows. The selected set failed the May
holdout decisively, and the best May pocket does not meet the requested
month-to-month stability standard.

The useful diagnostic is narrow: ETHUSDT EU-session late-flow exhaustion fade
can transfer positively into May, but only with an unstable pre-May profile.
That pocket remains research-only.

## Artifacts

- `data/research/wpr106_194_intrabar_flow_burst_profile_search/pre_may/intrabar_flow_pre_may_ranking.parquet`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/pre_may/intrabar_flow_pre_may_ranking.csv`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/pre_may/intrabar_flow_pre_may_monthly_returns.parquet`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/pre_may/selected_pre_may_rows.parquet`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/pre_may/selected_pre_may_rows.csv`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/pre_may/selected_pre_may_replay_metrics.csv`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/may_benchmark/selected_may_benchmark_metrics.csv`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/selected_pre_may_may_comparison.csv`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/wpr106_194_intrabar_flow_burst_profile_search_summary.json`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/wpr106_194_run_stdout.log`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/wpr106_194_run_stderr.log`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_194_intrabar_flow_burst_profile_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
