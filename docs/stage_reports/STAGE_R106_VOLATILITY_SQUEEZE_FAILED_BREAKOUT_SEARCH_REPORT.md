# Stage R106 Volatility Squeeze Failed-Breakout Search Report

Date: 2026-06-11
Packet: WPR106-121
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of all feature/filter threshold calibration, score-family
choice, side/session/regime choice, exit choice, ranking, and selection. May was
loaded only after the fixed pre-May loose selection table was written.

## Method

The runner
`data/research/wpr106_121_volatility_squeeze_failed_breakout_search/scripts/run_wpr106_121_volatility_squeeze_failed_breakout_search.py`
tests completed-bar 15m volatility-compression, breakout-confirmation,
failed-expansion, expansion-pullback, range-compression, flow-confirmed, and
no-flow control variants over the WPR106-96 verified feature frames.

Input features:

- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/features/btcusdt_features_price_trend_vol_2024_01_to_2026_05.parquet`
- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/features/ethusdt_features_price_perp_aggflow_no_wt_2024_01_to_2026_05.parquet`

Final fixed search grid:

- Symbols: BTCUSDT and ETHUSDT.
- Score families: failed expansion, flow-confirmed squeeze, no-flow control,
  range compression, squeeze, and volatility pullback.
- Filters: all, squeeze top 40%, release top 40%, failed-expansion top 40%.
- Sessions: all and US.
- Regimes: all, choppy, and high-volatility.
- Side modes: both, long, and short.
- Target raw signals per day: 1.0 and 2.5.
- Max accepted trades per day: 1 and 2.
- Exits: fixed 8, 16, and 32 bars, plus ATR barrier 32 bars with
  TP 1.5 ATR / SL 1.0 ATR.

The first broader grid attempt timed out before writing final evidence. The
closed packet uses the deterministic narrowed grid above. It produced 18,432
candidate rows. `cuda_used` is false and no speedup claim is made.

## Gates

Strict pre-May required:

- total net return above +0.04;
- at least 120 trades and 24 active months;
- 0.35 to 5.0 trades per active day;
- no more than 2 losing months in 2024, 2 in 2025, and 1 in Jan-Apr 2026;
- no more than 5 losing months overall;
- max drawdown above -0.25;
- cost-stress survival at least 0.75;
- best-month share at most 0.45;
- at most one rolling losing block;
- rolling minimum block return above -0.035.

Loose pre-May kept the same stability direction but relaxed the thresholds to
positive total return, at least 80 trades, at least 20 active months, 0.25 to
5.5 trades per active day, 3/3/1 annual losing-month caps, at most 7 losing
months overall, max drawdown above -0.35, cost-stress survival at least 0.50,
best-month share at most 0.60, and at most two rolling losing blocks.

## Artifacts

Root:
`data/research/wpr106_121_volatility_squeeze_failed_breakout_search/`

Key outputs:

- `wpr106_121_volatility_squeeze_failed_breakout_summary.json`
- `wpr106_121_runner.log`
- `pre_may/feature_manifest.csv`
- `pre_may/vol_squeeze_ranking.parquet`
- `pre_may/vol_squeeze_top2000.csv`
- `pre_may/selected_pre_may.csv`
- `pre_may/selected_pre_may_replay_metrics.csv`
- `pre_may/selected_pre_may_monthly_returns.parquet`
- `pre_may/selected_pre_may_daily_returns.parquet`
- `pre_may/selected_pre_may_trades.parquet`
- `may_benchmark/selected_may_benchmark_metrics.csv`
- `may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `may_benchmark/selected_may_benchmark_trades.parquet`

## Pre-May Results

Full grid:

- Candidate rows: 18,432.
- Positive pre-May rows: 1,998.
- Loose pre-May rows: 9.
- Strict pre-May rows: 0.

Family-level loose counts:

- Squeeze: 4 loose rows.
- Flow-confirmed squeeze: 2 loose rows.
- No-flow control: 2 loose rows.
- Failed expansion: 1 loose row.
- Volatility pullback: 0 loose rows.
- Range compression: 0 loose rows.

The 9 selected loose rows were concentrated in one shape:

- 8 ETHUSDT long US squeeze/breakout variants, mostly high-volatility regime,
  with squeeze-follow, flow-confirmed squeeze, and no-flow control templates.
- 1 BTCUSDT long choppy failed-expansion fade variant.
- All selected rows used fixed 32-bar exits.
- Trade counts ranged from 278 to 324.
- Trades per active day ranged from 1.000 to 1.113.
- Active months were 28 for every selected row.
- Losing months ranged from 6 to 7.
- Total pre-May net return ranged from +0.301687 to +1.157136.
- Worst pre-May month ranged from -0.074428 to -0.107057.
- Max drawdown ranged from -0.101092 to -0.216043.

The best selected pre-May rows were still loose, not strict:

- `vsqz-d73fcc9a5b4f9eb1`, ETHUSDT flow-confirmed squeeze breakout, US
  high-vol long fixed 32-bar exit: +1.157136 pre-May, 310 trades, 7 losing
  months, max drawdown -0.208825.
- `vsqz-4ac4b2284c085909`, ETHUSDT flow-confirmed squeeze breakout, US
  high-vol long fixed 32-bar exit: +1.147103 pre-May, 308 trades, 7 losing
  months, max drawdown -0.208825.
- `vsqz-e442df270b22614e`, ETHUSDT no-flow breakout control, US high-vol long
  fixed 32-bar exit: +0.987940 pre-May, 284 trades, 6 losing months, max
  drawdown -0.216043.

## May Benchmark

May benchmark was run only after fixed pre-May loose selection:

- Selected rows: 9.
- May-positive rows: 1.
- May-negative rows: 8.
- May-flat rows: 0.
- Best May return: +0.030321.
- Worst May return: -0.051256.
- Median May return: -0.036954.
- May trade count range: 12 to 14.
- May active-day range: 12 to 14.

The only May-positive row was the lowest-ranked selected row:

- `vsqz-16b31482d1e28cd2`, BTCUSDT failed-expansion fade, all-session choppy
  long fixed 32-bar exit: +0.030321 May, 14 trades, 12 active days.

The ETHUSDT selected rows failed as a group:

- The two top-ranked ETHUSDT flow-confirmed squeeze rows returned -0.051256 in
  May.
- Six ETHUSDT squeeze/no-flow rows returned -0.036954 in May.

## Decision

This packet rejects the volatility squeeze / failed-breakout source family as
candidate-ready evidence. The family can produce active one-trade-per-day
pre-May rows after costs and overlap handling, but it did not produce any
strict month-stable pre-May row. The loose rows were concentrated in ETHUSDT
long US/high-vol breakout behavior, retained 6 to 7 losing pre-May months, and
failed the fixed May benchmark with 8 of 9 rows negative.

The useful negative evidence is that a fresh compression-to-expansion family did
not rescue the 2024-forward stability problem. The single May-positive BTC
failed-expansion fade is not enough on its own: it was the lowest-ranked loose
row, had only +0.301687 pre-May return, 7 losing pre-May months, and no strict
pre-May stability pass.

Future work should move away from ETHUSDT US high-vol squeeze-follow behavior
and test a genuinely different source mechanism, such as multi-timeframe
regime-conditioned exits, causal volatility state transitions with dynamic
cooldowns, or a scoped model/feature variant whose pre-May stability is not
driven by one breakout window.

## Validation

Passed:

```powershell
python -m compileall -q data/research/wpr106_121_volatility_squeeze_failed_breakout_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
