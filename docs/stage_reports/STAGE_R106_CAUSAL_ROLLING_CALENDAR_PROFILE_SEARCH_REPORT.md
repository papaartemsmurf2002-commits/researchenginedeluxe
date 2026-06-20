# Stage R106 Causal Rolling Calendar Profile Search Report

Date: 2026-06-12
Packet: WPR106-140
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

All template, threshold, filter, ranking, and selection choices used only
2024-01-01 through 2026-04-30. May 2026 was held out of tuning and replayed only
after the fixed pre-May selection was written. May rolling-profile history was
frozen to labels completed before 2026-05-01, so no May outcome could influence
any May signal.

## Method

The runner
`data/research/wpr106_140_causal_rolling_calendar_profile_search/scripts/run_wpr106_140_causal_rolling_calendar_profile_search.py`
tests a causal follow-up to WPR106-139 over WPR106-96 verified BTCUSDT/ETHUSDT
15m bars plus 15m aggTrade-flow context.

Instead of fitting full-window pre-May calendar profiles, it builds same-bucket
rolling profile statistics from completed prior fixed-hold labels only. A prior
label is eligible only when its fixed-hold exit timestamp is before the current
signal timestamp. For May benchmark rows, the profile history is frozen to
labels completed before 2026-05-01.

Bucket modes:

- `session4`
- `weekday_session4`
- `hour`
- `weekday_hour`

Templates:

- `causal_rolling_profile_follow`
- `causal_rolling_profile_pullback`
- `causal_rolling_profile_momentum`
- `causal_rolling_flow_impulse`
- `causal_rolling_volatility_fade`

The search varies 4/8/16/32-bar fixed holds, rolling lookbacks of 64/256/1024
completed labels, minimum profile count 20, all/EU/US session filters,
all/high-volume volatility filters, all/confirm/contra/neutral flow filters,
and target raw signal rates of 1, 3, and 5 per day. Entries use the next bar
after the completed signal bar. Trade overlap, taker plus slippage/spread cost,
cost stress, monthly returns, drawdown, and active-rate metrics reuse the
recent artifact runner accounting.

## Results

Pre-May screen:

- Source rows per symbol: 84,672.
- Evaluated candidate rows: 34,560.
- Positive pre-May rows: 3,257.
- Annual-target rows: 115.
- Loose pre-May rows: 84.
- Strict pre-May rows: 0.
- Fixed selected rows: 84 loose rows.

Selected loose rows by family:

- ETHUSDT `rolling_calendar_profile`: 31.
- ETHUSDT `rolling_calendar_momentum`: 24.
- BTCUSDT `rolling_calendar_profile`: 10.
- ETHUSDT `rolling_calendar_flow_impulse`: 7.
- BTCUSDT `rolling_calendar_volatility_fade`: 6.
- BTCUSDT `rolling_calendar_momentum`: 3.
- BTCUSDT `rolling_calendar_flow_impulse`: 2.
- ETHUSDT `rolling_calendar_pullback`: 1.

The top selected loose row is:

- Candidate ID: `rollcal-06a7466e7ef2c748`.
- Symbol: ETHUSDT.
- Family/template: `rolling_calendar_flow_impulse` /
  `causal_rolling_flow_impulse`.
- Bucket mode: `weekday_hour`.
- Hold: 32 bars.
- Rolling lookback labels: 1,024.
- Session filter: US.
- Volatility filter: all.
- Flow filter: neutral.
- Target raw signals per day: 1.
- Trades: 114.
- Active days: 114.
- Trades per active day: 1.000000.
- Active months: 21.
- Losing months: 3.
- Annual losses: 2024: 0, 2025: 2, 2026 Jan-Apr: 1.
- Pre-May net return: +0.704749.
- Max drawdown: -0.195592.
- Sortino daily: 0.348412.
- Best-month share: 0.190797.
- Cost-stress survival: 4/4.

The largest pre-May loose return belonged to the second selected row,
`rollcal-7e31a5cbc122965d`, an ETHUSDT rolling profile-follow variant with
221 trades, 27 active months, 7 losing months, +1.055805 pre-May net return,
-0.179031 max drawdown, and full cost-stress survival. It was not strict
because it missed the annual-target/stability gates.

Month-to-month stability remained weak in the selected loose set. Across the
84 fixed loose rows, median pre-May row-level losing months was 8, and mean was
7.5. The basket's row-level monthly median was negative in July 2024
(-0.010679), March 2025 (-0.055176), April 2025 (-0.001097), December 2025
(-0.000324), and April 2026 (-0.005747).

May 2026 benchmark after fixed loose pre-May selection:

- May-positive selected rows: 12.
- May-negative selected rows: 58.
- May-flat selected rows: 14.
- Best May net return: +0.016704.
- Worst May net return: -0.123038.
- Median May net return: -0.014084.
- Mean May net return: -0.021735.

The best May row was `rollcal-041e2f0b40081226`, an ETHUSDT rolling momentum
variant with 4 May trades and +0.016704 May net return. The worst May row was
`rollcal-553d9b8309997181`, an ETHUSDT rolling momentum variant with 14 May
trades and -0.123038 May net return.

## Decision

The causal rolling calendar-profile family is rejected as a candidate lead. It
addresses the main WPR106-139 overfitting concern by using only completed prior
same-bucket labels, but that stricter construction produced no strict pre-May
rows. The fallback loose rows still looked active enough for research
diagnostics, but May 2026 was mostly negative after fixed pre-May selection and
frozen pre-May profile history.

Useful follow-up context: WPR106-140 suggests the WPR106-139 failure was not
only caused by full-window bucket leakage. Rolling causal time-bucket profiles
remain unstable across month boundaries, especially when momentum variants
select US high-volume/contra-flow conditions.

## Artifacts

- `data/research/wpr106_140_causal_rolling_calendar_profile_search/wpr106_140_causal_rolling_calendar_profile_summary.json`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/pre_may/rolling_calendar_ranking.parquet`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/pre_may/rolling_calendar_top2000.csv`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/pre_may/rolling_calendar_monthly_returns.parquet`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/pre_may/rolling_profile_diagnostics.parquet`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/pre_may/rolling_profile_diagnostics.csv`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/pre_may/family_summary.parquet`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/pre_may/family_summary.csv`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/pre_may/selected_pre_may.csv`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/pre_may/selected_pre_may_replay_metrics.csv`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/pre_may/selected_pre_may_trades.csv`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/may_benchmark/selected_may_benchmark_metrics.csv`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/may_benchmark/selected_may_benchmark_trades.csv`

## Validation

- `python -m compileall -q data/research/wpr106_140_causal_rolling_calendar_profile_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
