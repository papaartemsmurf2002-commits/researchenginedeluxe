# Stage R106 Microstructure State Transition Search Report

Date: 2026-06-12
Packet: WPR106-134
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of all feature, threshold, filter, hold, ranking, and
selection decisions. May was replayed only after fixed loose pre-May selection,
because no strict pre-May rows existed.

## Method

The runner
`data/research/wpr106_134_microstructure_state_transition_search/scripts/run_wpr106_134_microstructure_state_transition_search.py`
uses WPR106-126 source-context loading over WPR106-96 public-archive BTCUSDT
and ETHUSDT bars plus 15m aggTrade-flow aggregation.

Each symbol has 84,672 15m bars from 2024-01-01 through 2026-05-31. Signals
use completed 15m bars and enter on the next 15m open. Pre-May trades are
required to exit before 2026-05-01.

The grid covers:

- State windows: 96, 384, and 1,536 bars.
- Fixed holds: 4, 8, 16, and 32 bars.
- Sessions: all, Asia, EU, and US.
- State filters: all, streaking, flow-divergent, choppy, and burst.
- Flow filters: all, flow-confirmed, flow-contrarian, and flow-neutral.
- Target raw signals: 1, 3, and 5 per day.
- Families: return-streak continuation, return-streak exhaustion fade,
  flow-price agreement follow, flow-price divergence fade, volatility-burst
  follow, volatility-burst reversal, and alternating-chop reversion.

Costs use 0.0432% taker fee per side plus 0.0150% slippage/spread per side,
for 0.001164 round-trip cost. Cost stress tests 1.00x, 1.25x, 1.50x, and 2.00x
cost multipliers.

## Results

Full pre-May grid:

- Evaluated rows: 40,320.
- Positive pre-May rows: 4,070.
- Positive annual-target rows: 797.
- Loose rows: 55.
- Strict rows: 0.
- Selected rows: 55 loose rows.

The top selected loose pre-May row is:

- Symbol: ETHUSDT.
- Family: microstructure volatility-burst follow.
- Template: volatility-burst follow.
- State window: 384 bars.
- Hold: 32 bars.
- Session: EU.
- State filter: all.
- Flow filter: flow-neutral.
- Target signals per day: 5.
- Trades: 598.
- Active months: 28.
- Losing months: 8.
- Annual losses: 2024: 2, 2025: 5, 2026 Jan-Apr: 1.
- Pre-May net return: +1.333473.
- Max drawdown: -0.236297.
- Best-month share: 0.171097.
- Cost-stress survival: 4/4.

The annual-target rows are mostly too sparse for loose or strict selection.
The strongest annual-target diagnostic is BTCUSDT volatility-burst follow with
a 1,536-bar state window, 32-bar hold, Asia session, flow-divergent
flow-confirmed filters, 45 trades, 22 active months, 3 losing months, and
+0.307342 pre-May net return. It is not selected because it misses the trade
count and active-month coverage floors.

May 2026 benchmark after fixed loose pre-May selection:

- May-positive selected rows: 16.
- May-negative selected rows: 39.
- May-flat selected rows: 0.
- Best May net return: +0.037955.
- Worst May net return: -0.117907.
- Median May net return: -0.022664.

## Decision

The microstructure state-transition family is rejected as currently
configured. It finds many annual-target diagnostics, but those rows are
generally sparse and do not become strict or loose selections. The fixed loose
selection fails May 2026, with 39 negative rows versus 16 positive rows and a
negative median May return.

Useful follow-up context: flow-neutral volatility-burst follow and flow-price
agreement rows are the most productive active diagnostics, while the
annual-target rows show that flow-divergent/burst states can produce smoother
but sparse behavior. Future work should not promote these rows directly; any
new packet would need pre-May-only coverage repair, de-duplication, portfolio
construction, or a different exit model before another May benchmark.

## Artifacts

- `data/research/wpr106_134_microstructure_state_transition_search/wpr106_134_microstructure_state_transition_summary.json`
- `data/research/wpr106_134_microstructure_state_transition_search/pre_may/microstructure_state_transition_ranking.parquet`
- `data/research/wpr106_134_microstructure_state_transition_search/pre_may/microstructure_state_transition_top2000.csv`
- `data/research/wpr106_134_microstructure_state_transition_search/pre_may/microstructure_state_transition_monthly_returns.parquet`
- `data/research/wpr106_134_microstructure_state_transition_search/pre_may/family_summary.parquet`
- `data/research/wpr106_134_microstructure_state_transition_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_134_microstructure_state_transition_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_134_microstructure_state_transition_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_134_microstructure_state_transition_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_134_microstructure_state_transition_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_134_microstructure_state_transition_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_134_microstructure_state_transition_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_134_microstructure_state_transition_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_134_microstructure_state_transition_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_134_microstructure_state_transition_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
