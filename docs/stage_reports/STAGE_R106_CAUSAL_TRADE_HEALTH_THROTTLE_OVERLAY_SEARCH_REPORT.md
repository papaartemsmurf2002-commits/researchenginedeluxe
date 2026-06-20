# Stage R106 Causal Trade-Health Throttle Overlay Search Report

Date: 2026-06-11
Packet: WPR106-124
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of all source choice, overlay-policy choice, parameter
choice, ranking, and selection. Because no strict or loose pre-May overlay row
existed, May was not benchmarked for selected overlays.

## Method

The runner
`data/research/wpr106_124_causal_trade_health_throttle_overlay_search/scripts/run_wpr106_124_causal_trade_health_throttle_overlay_search.py`
tests causal trade-health filters around active WPR106-123 source rows. The
goal was to check whether the annual loss clusters in the active 15m
flow/price rows could be reduced by pause/resume logic that uses only realized
past accepted trades.

Inputs:

- `data/research/wpr106_123_flow_price_absorption_divergence_search/pre_may/selected_pre_may.csv`
- `data/research/wpr106_123_flow_price_absorption_divergence_search/pre_may/selected_pre_may_trades.parquet`

The 33 selected WPR106-123 diagnostics were deduplicated by actual pre-May
trade fingerprint into 18 unique source behaviors with 4,588 pre-May source
trades.

Overlay families:

- `baseline`: no throttle, for diagnostic comparison.
- `loss_cooldown`: skip 1, 2, or 4 source signals after an accepted losing
  trade.
- `daily_stop`: stop accepting trades for the rest of a day after accepted
  daily PnL reaches -0.5%, -1.0%, or -2.0%.
- `rolling_trade_health`: after accepted rolling 5/10/20-trade PnL falls below
  -1.0%, 0.0%, or +1.0%, skip 2 or 4 source signals.
- `monthly_health`: after an accepted active month returns <= -0.5% or <= 0.0%,
  skip the next 1 or 2 months.
- `hybrid`: combined monthly, daily, loss-cooldown, and rolling-trade gates.

For May, if any strict or loose overlay had existed, the runner would have
replayed source May trades through the fixed overlay while carrying pre-May
trade state forward. That path was not activated because no pre-May overlay
passed.

## Pre-May Results

Full grid:

- Source rows: 18.
- Source pre-May trades: 4,588.
- Overlay specs: 32.
- Candidate rows: 576.
- Positive pre-May rows: 498.
- Annual-target rows: 0.
- Overlay-loose rows: 0.
- Overlay-strict rows: 0.
- Selected diagnostic rows: 39.

Overlay-family summary:

- `monthly_health`: 72 rows, 66 positive, best +1.285117, active months up to
  23, lowest losing-month count 5, but 0 annual-target rows.
- `baseline`: 18 rows, all positive, best +1.233427, 28 active months, lowest
  losing-month count 9.
- `daily_stop`: 54 rows, all positive, best +1.233427, 28 active months,
  lowest losing-month count 9.
- `rolling_trade_health`: 324 rows, 273 positive, best +1.210776, 28 active
  months, lowest losing-month count 7.
- `loss_cooldown`: 54 rows, 43 positive, best +0.923284, 28 active months,
  lowest losing-month count 8.
- `hybrid`: 54 rows, 44 positive, best +0.617164, 28 active months, lowest
  losing-month count 5.

Representative diagnostics:

- `health124-13d5af0b1f29295b`, ETHUSDT flow-divergence source with rolling
  10-trade non-negative health and 4-signal cooldown: +1.106396 pre-May,
  223 trades, 28 active months, 9 losing months, max drawdown -0.135639.
- `health124-45ebdfdbc8b3d527`, ETHUSDT flow-follow source with rolling
  20-trade +1% health and 4-signal cooldown: +0.636129 pre-May, 143 trades,
  28 active months, 8 losing months, max drawdown -0.116851.
- `health124-ed46abe8cb0f8f62`, ETHUSDT flow-follow source with rolling
  10-trade +1% health and 2-signal cooldown: +0.656819 pre-May, 191 trades,
  28 active months, 7 losing months, max drawdown -0.185862.

The overlays reduced some drawdowns and skipped weak stretches, but they did
not meet the requested annual stability profile. The annual caps remained the
blocker.

## May Benchmark

May was not benchmarked because no selected row passed the strict or loose
pre-May gates. The runner wrote empty May benchmark tables and records:

- May 2026 benchmark-only: true.
- May 2026 used for selection: false.
- Selected May positive: 0.
- Selected May negative: 0.
- Selected May flat: 0.

## Decision

This packet rejects simple causal trade-health throttles as a repair for the
WPR106-123 active flow/price rows. The overlays can reduce drawdown and
sometimes reduce total losing months, but not enough to satisfy the annual
loss-count target. In particular, the policy family still cannot keep 2024 and
2025 to no more than two losing months each while maintaining sufficient
activity.

Future work should move to a different mechanism rather than adding more
trade-history throttles to the same source rows. A more meaningful next test
would be either a different feature/label family, a proper walk-forward model
with negative controls, or a cross-source regime selector that has independent
state information rather than using only the strategy's own realized PnL.

## Validation

Passed:

```powershell
python -m compileall -q data/research/wpr106_124_causal_trade_health_throttle_overlay_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
