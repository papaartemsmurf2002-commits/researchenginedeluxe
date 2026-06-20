# Stage R106 Prior-Day Level Gap Search Report

Date: 2026-06-11
Packet: WPR106-130
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of all feature, threshold, filter, hold, ranking, and
selection decisions. May was replayed only after fixed strict pre-May
selection.

## Method

The runner
`data/research/wpr106_130_prior_day_level_gap_search/scripts/run_wpr106_130_prior_day_level_gap_search.py`
uses WPR106-126 source-context loading over WPR106-96 public-archive BTCUSDT
and ETHUSDT bars plus 15m aggTrade-flow aggregation.

Each symbol has 84,672 15m bars from 2024-01-01 through 2026-05-31. Signals
use completed 15m bars and enter on the next 15m open. Pre-May trades are
required to exit before 2026-05-01.

The grid covers:

- Normalization windows: 96 and 384 bars.
- Fixed holds: 4, 8, 16, and 32 bars.
- Sessions: all, Asia, EU, and US.
- Volatility/volume filters: all, quiet-to-normal, high-volume, and high-range.
- Flow filters: all, flow-confirmed, flow-contrarian, and flow-neutral.
- Target raw signals: 1, 3, and 5 per day.
- Families: prior-day breakout follow, failed-breakout fade, prior-range fade,
  overnight gap reversion, overnight gap continuation, and prior-day VWAP
  reversion.

Costs use 0.0432% taker fee per side plus 0.0150% slippage/spread per side,
for 0.001164 round-trip cost. Cost stress tests 1.00x, 1.25x, 1.50x, and 2.00x
cost multipliers.

## Results

Full pre-May grid:

- Evaluated rows: 17,664.
- Positive pre-May rows: 2,061.
- Positive annual-target rows: 1.
- Loose rows: 105.
- Strict rows: 1.
- Selected rows: 1 strict row.

The strict pre-May row is:

- Symbol: ETHUSDT.
- Family: prior-day breakout.
- Template: prior-day breakout follow.
- Normalization window: 384 bars.
- Hold: 32 bars.
- Session: all.
- Volatility filter: high-range.
- Flow filter: flow-neutral.
- Target signals per day: 3.
- Trades: 261.
- Active months: 28.
- Losing months: 5.
- Annual losses: 2024: 2, 2025: 2, 2026 Jan-Apr: 1.
- Pre-May net return: +1.088169.
- Max drawdown: -0.126504.
- Best-month share: 0.163108.
- Cost-stress survival: 4/4.

The broader loose set has 105 rows and is dominated by ETHUSDT prior-day
breakout rows plus ETHUSDT gap-continuation diagnostics. BTCUSDT contributes
loose rows in breakout, failed-breakout, gap-continuation, gap-reversion, and
range-fade variants, but no BTCUSDT row is strict.

May 2026 benchmark after fixed strict pre-May selection:

- May-positive selected rows: 0.
- May-negative selected rows: 1.
- May-flat selected rows: 0.
- May trades: 3.
- May net return: -0.029037.
- May max drawdown: -0.029037.

## Decision

The prior-day level/gap family is rejected as currently configured. It found a
legitimate strict pre-May row, but the row failed the May 2026 benchmark
holdout. The result is useful because it narrows a stronger prior-day breakout
lead, but no candidate-ready, paper-ready, live-ready, or promotion-ready claim
exists.

Useful follow-up context: the rejected strict row is a high-range ETHUSDT
prior-day breakout follow. Future work should not promote it directly; it would
need new pre-May-only causal filters, complementary portfolio tests, or a
different exit model before any new May benchmark.

## Artifacts

- `data/research/wpr106_130_prior_day_level_gap_search/wpr106_130_prior_day_level_gap_summary.json`
- `data/research/wpr106_130_prior_day_level_gap_search/pre_may/prior_day_level_gap_ranking.parquet`
- `data/research/wpr106_130_prior_day_level_gap_search/pre_may/prior_day_level_gap_top2000.csv`
- `data/research/wpr106_130_prior_day_level_gap_search/pre_may/prior_day_level_gap_monthly_returns.parquet`
- `data/research/wpr106_130_prior_day_level_gap_search/pre_may/family_summary.parquet`
- `data/research/wpr106_130_prior_day_level_gap_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_130_prior_day_level_gap_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_130_prior_day_level_gap_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_130_prior_day_level_gap_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_130_prior_day_level_gap_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_130_prior_day_level_gap_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_130_prior_day_level_gap_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_130_prior_day_level_gap_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_130_prior_day_level_gap_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_130_prior_day_level_gap_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
