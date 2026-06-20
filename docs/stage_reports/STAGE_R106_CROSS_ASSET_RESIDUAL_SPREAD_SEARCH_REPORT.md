# Stage R106 WPR106-195 Cross-Asset Residual Spread Search Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-195 continued the broad 2024-forward search after WPR106-194 rejected
single-leg intrabar flow-burst entries. It tested BTC/ETH equal-notional
relative-value pair entries using causal rolling residuals, flow divergence,
volatility state, and session filters.

All residual windows, templates, thresholds, hold/session/side/daily-cap
choices, row ranking, and selected-row inclusion used only 2024-01-01 through
2026-04-30 UTC. May 2026 was replayed only after fixed pre-May selection.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_195_cross_asset_residual_spread_search/scripts/run_wpr106_195_cross_asset_residual_spread_search.py`

The runner imports WPR106-170 helpers for aligned WPR106-96 BTCUSDT/ETHUSDT
contexts, period masks, embedded costs, overlap blocking, monthly metrics,
annual losing-month checks, drawdown, Sortino, and cost-stress accounting.

Each trade is an equal-notional pair:

- positive pair side means long target symbol and short hedge symbol;
- negative pair side means short target symbol and long hedge symbol;
- gross return is 50% target leg return plus 50% hedge leg return;
- round-trip cost uses the WPR106 notional cost policy for the pair notional.

The grid evaluates BTCUSDT-target and ETHUSDT-target variants across:

- residual windows of 384 and 1,536 bars;
- 4/8/16/32-bar holds;
- all/Asia/EU/US sessions;
- target raw rates of 1/3/5 signals per day;
- both/long/short side modes;
- daily caps of 1/3/5;
- templates for residual reversion, residual breakout follow, flow-divergence
  reversion, volatility-adjusted spread follow, and quiet residual reversion.

Runtime was 83.39 seconds. CUDA was not used and no speedup claim was made.

## Results

Pre-May screen:

- 8,640 evaluated rows.
- 564 positive pre-May rows.
- 52 annual-target rows.
- 0 loose rows.
- 0 strict rows.

Pre-May by strongest templates:

- BTCUSDT/ETHUSDT `residual_breakout_follow`: 168 positive rows per target,
  12 annual-target rows per target, best +0.227714.
- BTCUSDT/ETHUSDT `residual_reversion`: 52 positive rows per target, 11
  annual-target rows per target, best +0.077771.
- BTCUSDT `vol_adjusted_spread_follow`: 36 positive rows, no annual-target
  rows, best +0.130022.

The annual-target rows were not usable leads. Their median trade counts were
10 to 15 trades depending on template and none passed latest-four-month floors
of at least three active months and at least 20 trades.

Fixed selected set:

- 15 selected rows.
- All 15 are `positive_recent_stability` fallback rows.
- 8 BTCUSDT-target rows and 7 ETHUSDT-target rows.
- 14 `residual_breakout_follow` rows and 1 `vol_adjusted_spread_follow` row.

Selected pre-May replay:

- 15 positive rows, 0 negative rows, 0 flat rows.
- Median net return: +0.104935.
- Active mean net return: +0.122760.
- Best/worst selected rows: +0.192660 / +0.058794.

May 2026 benchmark replay:

- 15 active rows.
- 0 positive rows and 15 negative rows.
- Median net return: -0.012385.
- Active mean net return: -0.016748.
- Best/worst selected rows: -0.002851 / -0.030679.

The least-bad May row was `spread195-79a8bd3c6bd74c14`: BTCUSDT target,
ETHUSDT hedge, `vol_adjusted_spread_follow`, 1,536-bar residual window,
32-bar hold, all-session, both-sided, daily cap 1. It had +0.130022 pre-May
over 240 trades, 28 active months, 11 losing months, max drawdown -0.098473,
and 50% cost-stress survival, but May was still negative at -0.002851.

## Interpretation

WPR106-195 is rejected as candidate-ready, portfolio-ready, or
promotion-ready. The pair-spread family reduced drawdowns compared with recent
single-leg pockets and generated sparse annual-target rows, but active
selected rows failed the May holdout uniformly. The annual-target pockets were
too sparse and too inactive recently to justify a benchmark lead.

The useful diagnostic is that BTC/ETH residual spreads improve drawdown shape
but currently do not solve month-to-month stability or May transfer.

## Artifacts

- `data/research/wpr106_195_cross_asset_residual_spread_search/pre_may/pair_spread_pre_may_ranking.parquet`
- `data/research/wpr106_195_cross_asset_residual_spread_search/pre_may/pair_spread_pre_may_ranking.csv`
- `data/research/wpr106_195_cross_asset_residual_spread_search/pre_may/pair_spread_pre_may_monthly_returns.parquet`
- `data/research/wpr106_195_cross_asset_residual_spread_search/pre_may/selected_pre_may_rows.parquet`
- `data/research/wpr106_195_cross_asset_residual_spread_search/pre_may/selected_pre_may_rows.csv`
- `data/research/wpr106_195_cross_asset_residual_spread_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_195_cross_asset_residual_spread_search/pre_may/selected_pre_may_replay_metrics.csv`
- `data/research/wpr106_195_cross_asset_residual_spread_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_195_cross_asset_residual_spread_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_195_cross_asset_residual_spread_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_195_cross_asset_residual_spread_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_195_cross_asset_residual_spread_search/may_benchmark/selected_may_benchmark_metrics.csv`
- `data/research/wpr106_195_cross_asset_residual_spread_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_195_cross_asset_residual_spread_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_195_cross_asset_residual_spread_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_195_cross_asset_residual_spread_search/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_195_cross_asset_residual_spread_search/selected_pre_may_may_comparison.csv`
- `data/research/wpr106_195_cross_asset_residual_spread_search/wpr106_195_cross_asset_residual_spread_search_summary.json`
- `data/research/wpr106_195_cross_asset_residual_spread_search/wpr106_195_run_stdout.log`
- `data/research/wpr106_195_cross_asset_residual_spread_search/wpr106_195_run_stderr.log`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_195_cross_asset_residual_spread_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
