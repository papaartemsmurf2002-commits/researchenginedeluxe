# Stage R106 Flow-Price Absorption Divergence Search Report

Date: 2026-06-11
Packet: WPR106-123
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of all feature/filter threshold calibration, score-family
choice, side/session/regime choice, exit choice, ranking, and selection.
Because no strict or loose pre-May row existed, May was not benchmarked for
selected rows.

## Method

The runner
`data/research/wpr106_123_flow_price_absorption_divergence_search/scripts/run_wpr106_123_flow_price_absorption_divergence_search.py`
tests completed-bar 15m flow/price absorption and divergence scores over the
WPR106-96 verified feature frames. It reuses the WPR106-115 completed-bar
evaluation primitives for costs, sessions, regimes, overlap blocking, day caps,
fixed exits, monthly diagnostics, rolling-block diagnostics, and cost stress.

Input features:

- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/features/btcusdt_features_price_trend_vol_2024_01_to_2026_05.parquet`
- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/features/ethusdt_features_price_perp_aggflow_no_wt_2024_01_to_2026_05.parquet`

Feature coverage:

- BTCUSDT has 84,672 rows from 2024-01-01 through 2026-05-31 and basic taker
  quote proxy context from the 15m feature frame.
- ETHUSDT has 84,672 rows from 2024-01-01 through 2026-05-31 and richer
  aggTrade proxy columns, including signed quote imbalance, CVD-slope proxy,
  and flow-burst proxy.

The first implementation attempted a broader grid. That run timed out before
writing final evidence. The final fixed run used a narrower deterministic grid:

- Score families: flow absorption, flow divergence, flow exhaustion,
  flow-follow, flow-pullback, and no-flow price-only exhaustion control.
- Filters: all rows, flow-active top 40%, and absorption top 40%.
- Sessions: all and US.
- Regimes: all and flow-active.
- Side modes: long and short.
- Target raw signals per day: 1.0 and 2.5.
- Max accepted trades per day: 1 and 2.
- Exits: fixed 16 bars and fixed 32 bars.

## Pre-May Results

Full grid:

- Candidate rows: 2,304.
- Positive pre-May rows: 343.
- Annual-target pre-May rows: 182.
- Flow-loose rows: 0.
- Flow-strict rows: 0.
- Selected diagnostic rows: 33.

Family-level diagnostics:

- ETHUSDT flow-pullback had 86 annual-target rows, but positive annual-target
  rows maxed out at only 8 trades and 8 active months.
- BTCUSDT flow-pullback had 96 annual-target rows, but positive annual-target
  rows maxed out at only 3 trades and 2 active months.
- ETHUSDT flow-divergence and flow-follow each had 67 positive rows, with best
  pre-May return +1.233427, but no annual-target rows.
- BTCUSDT flow-follow had 42 positive rows, best +0.275373, but no annual
  target.
- No-flow price-only controls had zero positive rows for both symbols.

Selected diagnostic rows were all `active_coverage_annual_fail` rows:

- Active months: 28 for every selected row.
- Trades: 140 to 515.
- Losing months: 9 to 11.
- Pre-May return: +0.154603 to +1.233427.
- Best rows were ETHUSDT flow-divergence / flow-confirmed-breakout long
  fixed-32 variants.
- The strongest return rows still had 4 to 5 losing months in 2024 and 4 to 6
  losing months in 2025, violating the requested annual stability profile.

Representative active diagnostics:

- `flow15-641d77fcca702f89`, ETHUSDT flow-price divergence fade, absorption
  top 40%, all session/all regime, long fixed 32 bars: +1.233427 pre-May,
  427 trades, 28 active months, 11 losing months, max drawdown -0.213945.
- `flow15-d5ef683a1d82cbba`, ETHUSDT flow-price divergence fade, absorption
  top 40%, all session/all regime, long fixed 32 bars: +1.148251 pre-May,
  515 trades, 28 active months, 9 losing months, max drawdown -0.335884.
- `flow15-74ab641dde07be04`, ETHUSDT flow-follow, absorption top 40%, US/all,
  long fixed 32 bars: +0.851069 pre-May, 279 trades, 28 active months,
  10 losing months, max drawdown -0.169773.

Annual-target rows were not viable active leads:

- Positive annual-target rows maxed at 8 trades and 8 active months.
- Best annual-target row was ETHUSDT flow-pullback long fixed 32 bars at
  +0.072674 pre-May, 8 trades, 8 active months, 2 losing months, and
  best-month share 0.686905.

## May Benchmark

May was not benchmarked because no selected row passed the strict or loose
pre-May gates. The runner wrote empty May benchmark tables and records:

- May 2026 benchmark-only: true.
- May 2026 used for selection: false.
- Selected May positive: 0.
- Selected May negative: 0.
- Selected May flat: 0.

## Decision

This packet rejects the 15m flow/price absorption-divergence family as
candidate-ready evidence. The richer ETHUSDT aggTrade proxy can produce active,
cost-positive pre-May rows, but those rows do not meet the month-to-month
stability target. Rows that satisfy annual loss limits are too sparse to be
credible active leads.

The useful result is that this mechanism is not simply blocked by trade
frequency or costs: active 15m flow-divergence rows exist and can generate many
entries after overlap/day-cap handling. The blocker is annual stability, not
activity. Future work should not treat these ETHUSDT flow-divergence/follow
long fixed-32 rows as leads unless a genuinely new filter removes the 2024 and
2025 loss clusters without using May.

## Validation

Passed:

```powershell
python -m compileall -q data/research/wpr106_123_flow_price_absorption_divergence_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
