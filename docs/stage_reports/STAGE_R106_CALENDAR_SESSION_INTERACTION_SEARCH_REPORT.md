# Stage R106 Calendar Session Interaction Search Report

Date: 2026-06-12
Packet: WPR106-139
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of feature construction, calendar-profile fitting,
template choice, threshold choice, filter choice, ranking, and fixed selection.
May was replayed only after the fixed strict pre-May rows were selected.

## Method

The runner
`data/research/wpr106_139_calendar_session_interaction_search/scripts/run_wpr106_139_calendar_session_interaction_search.py`
tests frozen pre-May calendar/session profiles over WPR106-96 verified
BTCUSDT/ETHUSDT 15m bars plus 15m aggTrade-flow context.

It fits completed-bar profiles on 2024-01-01 through 2026-04-30 only. For each
symbol, bucket mode, and hold horizon, it measures the pre-May next-entry fixed
hold return by bucket, then freezes the bucket direction and strength for both
pre-May ranking and May benchmark. Bucket modes:

- `session4`
- `weekday_session4`
- `hour`
- `weekday_hour`

Templates:

- `calendar_profile_follow`
- `calendar_profile_pullback`
- `calendar_profile_momentum`
- `flow_confirmed_calendar_impulse`
- `volatility_calendar_fade`

The search varies 4/8/16/32-bar fixed holds, all/Asia/EU/US session filters,
all/quiet/high-range/high-volume volatility filters, all/confirm/contra/neutral
flow filters, and target raw signal rates of 1, 3, and 5 per day. Entries use
the next bar after the completed signal bar. Trade overlap, taker plus
slippage/spread cost, cost stress, monthly returns, drawdown, and active-rate
metrics reuse the recent artifact runner accounting.

## Results

Pre-May screen:

- Source rows per symbol: 84,672.
- Evaluated candidate rows: 29,184.
- Positive pre-May rows: 9,735.
- Annual-target rows: 237.
- Loose pre-May rows: 808.
- Strict pre-May rows: 17.
- Fixed selected rows: 17 strict rows.

Strict rows by family:

- ETHUSDT `calendar_session_momentum`: 8.
- ETHUSDT `calendar_flow_impulse`: 4.
- ETHUSDT `calendar_session_profile`: 3.
- BTCUSDT `calendar_session_profile`: 2.

The top selected strict row is:

- Candidate ID: `calendar-31c7fbe72a20a7ac`.
- Symbol: ETHUSDT.
- Family/template: `calendar_flow_impulse` /
  `flow_confirmed_calendar_impulse`.
- Bucket mode: `weekday_hour`.
- Hold: 32 bars.
- Session filter: all.
- Volatility filter: high volume.
- Flow filter: all.
- Target raw signals per day: 3.
- Trades: 678.
- Active days: 486.
- Trades per active day: 1.395062.
- Active months: 28.
- Losing months: 4.
- Annual losses: 2024: 2, 2025: 1, 2026 Jan-Apr: 1.
- Pre-May net return: +2.480657.
- Max drawdown: -0.205831.
- Sortino daily: 0.350700.
- Best-month share: 0.125698.
- Cost-stress survival: 4/4.

May 2026 benchmark after fixed strict pre-May selection:

- May-positive selected rows: 0.
- May-negative selected rows: 17.
- May-flat selected rows: 0.
- Best May net return: -0.000748.
- Worst May net return: -0.133646.
- Median May net return: -0.033021.
- The top selected row had 24 May trades over 17 active days and returned
  -0.000748.

## Decision

The calendar/session interaction family is rejected as a candidate lead. It
creates active, strict-looking pre-May rows with normal 1-5 trades/day behavior
and broad 28-month coverage, but all fixed strict rows lose in the untouched
May 2026 benchmark. This suggests the fitted weekday/hour profile is unstable
across the holdout month rather than a robust edge.

Useful follow-up context: the family is a good negative control for
time-of-week overfitting. It can produce large pre-May returns when bucket
direction is fitted across the full optimization window, but the May result
shows that this profile-fitting approach should not be defended without a
walk-forward or rolling-profile variant.

## Artifacts

- `data/research/wpr106_139_calendar_session_interaction_search/wpr106_139_calendar_session_interaction_summary.json`
- `data/research/wpr106_139_calendar_session_interaction_search/pre_may/calendar_session_ranking.parquet`
- `data/research/wpr106_139_calendar_session_interaction_search/pre_may/calendar_session_top2000.csv`
- `data/research/wpr106_139_calendar_session_interaction_search/pre_may/calendar_session_monthly_returns.parquet`
- `data/research/wpr106_139_calendar_session_interaction_search/pre_may/frozen_pre_may_calendar_profiles.parquet`
- `data/research/wpr106_139_calendar_session_interaction_search/pre_may/frozen_pre_may_calendar_profiles.csv`
- `data/research/wpr106_139_calendar_session_interaction_search/pre_may/family_summary.parquet`
- `data/research/wpr106_139_calendar_session_interaction_search/pre_may/family_summary.csv`
- `data/research/wpr106_139_calendar_session_interaction_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_139_calendar_session_interaction_search/pre_may/selected_pre_may.csv`
- `data/research/wpr106_139_calendar_session_interaction_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_139_calendar_session_interaction_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_139_calendar_session_interaction_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_139_calendar_session_interaction_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_139_calendar_session_interaction_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_139_calendar_session_interaction_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_139_calendar_session_interaction_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_139_calendar_session_interaction_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_139_calendar_session_interaction_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
