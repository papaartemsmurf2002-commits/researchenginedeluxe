# Stage R106 Intrabar Order-Flow Event Search Report

Date: 2026-06-12
Packet: WPR106-153
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of all feature, threshold, state-filter, side-mode,
daily-cap, throttle, exit, ranking, and selection decisions. May was replayed
only after fixed loose pre-May rows were selected.

## Method

The runner
`data/research/wpr106_153_intrabar_order_flow_event_search/scripts/run_wpr106_153_intrabar_order_flow_event_search.py`
loads WPR106-96 BTCUSDT/ETHUSDT 15m bars and 1m aggTrade context. Each symbol
has 84,672 15m bars from 2024-01-01 through 2026-05-31. The 1m aggTrade files
have 1,270,046 rows per symbol over the same window.

Signals use completed 15m bars and enter on the next 15m open. Pre-May trades
are required to exit before 2026-05-01.

The packet materializes 15m features from 1m intrabar order-flow shape:

- signed quote imbalance;
- first-three-minute and last-three-minute signed delta;
- late-volume share;
- top-three-minute volume concentration;
- flow flip/acceleration;
- price response, range, and efficiency;
- absorption and flow/price divergence proxies.

The grid covers:

- Normalization windows: 96 and 384 bars.
- Fixed holds: 4, 8, 16, and 32 bars.
- Sessions: all and US.
- Intrabar state filters: all, flow burst, volume burst, late flow,
  concentrated, absorption, and flip.
- Side modes: both, long-only, and short-only.
- Target raw signals: 1, 3, and 5 per day.
- Accepted-trade daily caps: 1, 3, and 5.
- Loss-throttle modes: none and skip after one prior completed losing month.
- Templates: flow burst follow, flow burst fade, absorption fade, late delta
  flip follow, late delta flip fade, volume climax reversal, and flow/price
  divergence fade.

Costs use the same research fee/slippage model as recent packets:
0.0432% taker fee per side plus 0.0150% slippage/spread per side, for
0.001164 round-trip cost. Cost stress tests 1.00x, 1.25x, 1.50x, and 2.00x
cost multipliers through the reused WPR106 monthly metrics.

## Results

Full pre-May grid:

- Evaluated rows: 84,672.
- Positive pre-May rows: 1,730.
- Positive annual-target rows: 0.
- Loose rows: 138.
- Strict rows: 0.
- Selected rows: 100 loose rows.

Selected pre-May rows:

- Net-return range: +0.103158 to +0.955683.
- Trade-count range: 223 to 588.
- Active-month range: 20 to 28.
- Losing-month range: 6 to 8.
- No selected row meets annual loss caps.

The top selected loose row is:

- Candidate: `intrabarof-423ffe9e90d52a36`.
- Symbol: ETHUSDT.
- Family/template: intrabar late-delta flip fade / late-delta flip fade.
- Normalization window: 384 bars.
- Hold: 32 bars.
- Session: US.
- State filter: late flow.
- Side mode: long-only.
- Target raw signals: 1 per day.
- Accepted-trade daily cap: 3.
- Loss throttle: none.
- Trades: 521.
- Active months: 28.
- Losing months: 8.
- Annual losses: 2024: 3, 2025: 4, 2026 Jan-Apr: 1.
- Pre-May net return: +0.955683.
- Max drawdown: -0.262727.
- Best-month share: 0.126263.
- Cost-stress survival: 4/4.

Family diagnostics:

- ETHUSDT late-delta flip fade is the strongest active family, led by the
  top selected row above.
- BTCUSDT late-delta flip fade and volume-climax reversal produce active loose
  rows but miss annual stability.
- Flow/price divergence can be May-positive in some selected rows, especially
  BTCUSDT volume-burst variants, but those rows still have 7 to 8 pre-May
  losing months.

May 2026 benchmark after fixed loose pre-May selection:

- May-positive selected rows: 30.
- May-negative selected rows: 46.
- May-flat selected rows: 24.
- Best May return: +0.049922.
- Worst May return: -0.141880.
- Median May return: 0.000000.

The best May row is an ETHUSDT concentrated late-delta flip fade variant with
+0.049922 May return and 22 May trades, but its pre-May annual losses are
2024: 4, 2025: 2, 2026 Jan-Apr: 1, so it was already outside the requested
annual stability target. The top pre-May row benchmarks -0.057689 in May.

## Decision

The intrabar order-flow event family is rejected as currently configured. It
uses the richer 1m aggTrade order-flow shape and produces active, cost-positive
pre-May rows, but the annual stability target is never met. The blocker is not
data coverage, activity, or basic costs; it is month-to-month loss clustering.

This result improves the earlier 15m flow evidence by showing that intrabar
late-delta and concentration features can create stronger active rows and some
May-positive diagnostics, but they still do not support a candidate-ready,
paper-ready, live-ready, or promotion-ready claim.

Useful follow-up context: a future order-flow packet should not promote these
rows directly. It would need a new pre-May-only stability repair, different
exit model, portfolio construction, or additional context that specifically
targets the 2024 and 2025 loss clusters.

## Artifacts

- `data/research/wpr106_153_intrabar_order_flow_event_search/wpr106_153_intrabar_order_flow_summary.json`
- `data/research/wpr106_153_intrabar_order_flow_event_search/pre_may/intrabar_order_flow_ranking.parquet`
- `data/research/wpr106_153_intrabar_order_flow_event_search/pre_may/intrabar_order_flow_top2000.csv`
- `data/research/wpr106_153_intrabar_order_flow_event_search/pre_may/intrabar_order_flow_monthly_returns.parquet`
- `data/research/wpr106_153_intrabar_order_flow_event_search/pre_may/family_summary.parquet`
- `data/research/wpr106_153_intrabar_order_flow_event_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_153_intrabar_order_flow_event_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_153_intrabar_order_flow_event_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_153_intrabar_order_flow_event_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_153_intrabar_order_flow_event_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_153_intrabar_order_flow_event_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_153_intrabar_order_flow_event_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_153_intrabar_order_flow_event_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_153_intrabar_order_flow_event_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_153_intrabar_order_flow_event_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
