# WPR106-169 Broad Bar-State Flow Interaction Screen

Status: closed
Date: 2026-06-12
Stage: R106 strategy research

## Objective

Run a broader 2024-forward research-only screen over completed 15m BTCUSDT and
ETHUSDT bar state, aggTrade-flow proxy state, and cross-symbol interaction
scores. This packet follows the WPR106-168 negative fresh-holdout result by
returning to broad search rather than defending the rejected WPR146 threshold-5
descriptor.

The default optimization/search window is 2024-01-01 through 2026-04-30 UTC.
May 2026 must remain fully out of all scoring, feature choice, filter choice,
threshold choice, exit choice, ranking, and selection. May 2026 is used only as
a benchmark after pre-May candidates are fixed.

## Allowed Paths

- `docs/work_packets/WPR106-169-broad-bar-state-flow-interaction-screen.md`
- `docs/stage_reports/STAGE_R106_BROAD_BAR_STATE_FLOW_INTERACTION_SCREEN_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_169_broad_bar_state_flow_interaction_screen/**`

## Inputs

- Read-only WPR106-96 BTCUSDT and ETHUSDT source context under
  `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/**`.
- Read-only prior reports for WPR106-125 and WPR106-150 pair relative-value
  rejection context.

## Method

- Build aligned BTCUSDT and ETHUSDT 15m contexts from 2024-01-01 through
  2026-05-31, joining 1m aggTrade-flow proxy into completed 15m bars.
- Generate causal completed-bar score families from price path, volatility,
  wick/close-location, flow, volume, and cross-symbol relative state.
- Search BTCUSDT and ETHUSDT separately over:
  - 96/384/1536-bar normalization windows;
  - fixed holds of 8/16/32/64 bars;
  - all/Asia/EU/US sessions;
  - all/high-range/compressed-prior volatility gates;
  - all/flow-confirm/flow-contra/flow-neutral flow gates;
  - both/long-only/short-only side modes;
  - target raw signal rates of 1/3/5 per active day;
  - accepted-trade daily caps of 1/3/5.
- Apply one-position-at-a-time overlap handling, realistic round-trip costs,
  and cost-stress survival checks.
- Rank and select only from pre-May evidence with month-to-month stability
  emphasized over aggregate return.
- Replay fixed selected rows on May 2026 only after selection is complete.
- Keep outputs research-only, observe-only, and `promotion_ready: false`.

## Validation

- `python -m compileall -q data/research/wpr106_169_broad_bar_state_flow_interaction_screen/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

## Exit Criteria

- Write pre-May ranking, monthly returns, selected rows, selected pre-May
  replay details, May benchmark metrics/trades, summary JSON, and stage report.
- Update the stage ledger with the packet decision.
- Do not write a candidate pack or make paper/live/promotion claims.

## Result

WPR106-169 completed a broad completed-bar state, aggTrade-flow proxy, and
cross-symbol interaction screen over BTCUSDT and ETHUSDT 15m context from
2024-01-01 through 2026-04-30, with May 2026 held out of selection and used
only after fixed pre-May rows were selected.

The vectorized artifact runner evaluated 248,832 pre-May rows across
BTCUSDT/ETHUSDT, eight score templates, three normalization windows, four hold
horizons, session gates, volatility gates, flow gates, side modes, target
signal rates, and accepted-trade daily caps. It found 40,753 positive pre-May
rows, 2,042 annual-target rows, 384 loose rows, and zero strict rows. The top
100 selected rows were all loose and positive pre-May, but zero were strict.
Selected rows had median +0.952125 pre-May net, 25 to 28 active months, 4 to 8
losing months, 79 to 485 trades, full pre-May cost-stress survival, and median
one trade per active day.

May 2026 benchmark for the fixed top 100 selected rows was mixed and not
candidate-ready: 31 positive, 69 negative, 0 flat, best +0.048723, worst
-0.177795, median -0.042965, and 31 rows with positive May cost-stress
survival. The best May row was an ETHUSDT Asia-session volatility-breakout
continuation variant with flow-contra filtering, 64-bar hold, 1536-bar
normalization, and target three raw signals per day; it had +0.811320 pre-May
net and +0.048723 May net, but still had seven pre-May losing months, annual
losses 3/3/1, -0.265408 max drawdown, and therefore remains only a
research-only follow-up clue.

The packet rejects this broad bar-state/flow interaction screen as
candidate-ready, portfolio-ready, or promotion-ready evidence because no strict
pre-May row exists and the May benchmark is negative for the selected set as a
whole. It preserves the ETHUSDT flow-contra volatility-breakout/Asia pocket as
a possible later research clue requiring pre-May-only causal repair. No
candidate pack, paper/live artifact, live config, order path, sizing change,
CUDA speedup claim, or promotion claim was written. Focused script compile,
package compile, and contracts passed; contracts reported 460 passed.
