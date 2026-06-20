# WPR106-153 Intrabar Order-Flow Event Search

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Revisit order-flow and microstructure-style strategies using the 1m aggTrade
source context instead of only 15m aggregate flow features. This packet tests
whether intrabar flow shape, late delta, volume concentration, flow/price
absorption, and flow-flip behavior can produce month-stable active rows over
2024-forward BTCUSDT/ETHUSDT.

The goal is month-to-month stability with active behavior allowed around 1 to
5 accepted trades per active day after overlap, daily caps, and costs.

## Allowed Paths

- `docs/work_packets/WPR106-153-intrabar-order-flow-event-search.md`
- `docs/stage_reports/STAGE_R106_INTRABAR_ORDER_FLOW_EVENT_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_153_intrabar_order_flow_event_search/**`

## Inputs

- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/**`
- Rejection context from WPR106-123, WPR106-134, WPR106-149, and WPR106-152.
- Generic evaluation helpers from prior artifact-only WPR106 runners may be
  imported for source loading, period masks, costs, overlap, daily caps, and
  monthly stability metrics.

May 2026 may be loaded only after fixed pre-May survivors are selected. No May
data may influence feature choice, filter choice, threshold, exit rule,
ranking, or selection.

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, live configuration write, or promotion claim.
- Use 2024-01-01 through 2026-04-30 for every tuning and selection decision.
- Use May 2026 only as benchmark holdout if fixed pre-May survivors exist.
- Signals use completed 15m bars and enter on the next 15m open.
- Pre-May trades must exit before 2026-05-01.
- This packet is artifact-only and does not change shared strategy, feature,
  KNN, backtest, live, or candidate-pack code.
- CUDA is not expected; report CPU/vectorized/cached execution truthfully.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Load BTCUSDT/ETHUSDT 15m bars and 1m aggTrade context from WPR106-96.
2. Materialize 15m completed-bar features from 1m intrabar order-flow shape:
   - signed quote imbalance;
   - first-three-minute and last-three-minute delta;
   - late-volume share;
   - top-three-minute volume concentration;
   - flow flip/acceleration;
   - price response to signed flow;
   - absorption and divergence proxies.
3. Test order-flow event templates:
   - burst follow;
   - burst fade;
   - absorption fade;
   - late delta flip follow;
   - late delta flip fade;
   - volume-climax reversal;
   - flow/price divergence fade.
4. Search 96/384-bar normalizations, 4/8/16/32-bar fixed exits, all/US
   sessions, intrabar state filters, both/long-only/short-only side modes,
   target raw signal rates of 1/3/5 per day, accepted-trade caps of 1/3/5, and
   optional prior completed-month loss throttle.
5. Require strict or loose pre-May monthly stability before any May replay.
6. Replay May 2026 only for fixed pre-May survivors.
7. Record whether this intrabar order-flow family is rejected or whether a
   research-only follow-up lead deserves deeper controls.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_153_intrabar_order_flow_event_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

## Evidence Results

- Evaluated rows: 84,672.
- Positive pre-May rows: 1,730.
- Positive annual-target rows: 0.
- Loose pre-May rows: 138.
- Strict pre-May rows: 0.
- Selected rows: 100 loose rows.
- May benchmark: 30 positive rows, 46 negative rows, 24 flat rows.
- Best selected May return: +0.049922.
- Worst selected May return: -0.141880.
- Median selected May return: 0.000000.

The top selected loose row was ETHUSDT late-delta-flip fade, 384-bar
normalization, 32-bar hold, US session, late-flow state, long-only, target 1
raw signal/day, max 3 accepted trades/day, and no monthly loss throttle. It had
521 pre-May trades, 28 active months, 8 losing months, annual losses 2024: 3,
2025: 4, 2026 Jan-Apr: 1, +0.955683 pre-May net return, -0.262727 max
drawdown, 0.126263 best-month share, and 4/4 cost-stress survival. Its May
benchmark lost -0.057689 across 24 trades.

## Closeout

WPR106-153 rejects the intrabar order-flow event family as candidate-ready or
as a new promising lead. The packet finds active cost-positive rows using 1m
aggTrade intrabar flow shape, and some fixed selected rows are May-positive,
but no pre-May row meets the annual stability target. All positive rows have at
least 6 losing months, and all loose rows have 6 to 8 losing months.

The result is useful because the blocker is not data coverage, trade
frequency, or round-trip costs. Intrabar late-delta flip fade, flow/price
divergence, and volume-climax reversal produce active evidence, but the annual
loss clusters remain too large for the requested stability profile.

No candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim exists.

Validation passed:

```powershell
python -m compileall -q data/research/wpr106_153_intrabar_order_flow_event_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts result: 460 passed.
