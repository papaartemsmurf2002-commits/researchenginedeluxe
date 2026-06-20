# WPR106-151 Causal Multi-Day Level Retest Search

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Revisit the rejected prior-day level, sweep/wick, and opening-range families
without defending their old rows. This packet searches completed daily,
multi-day, and weekly level break, failed-break, retest, and midline-reversion
variants over the 2024-forward BTCUSDT/ETHUSDT context.

The goal is month-to-month stability, not one large profitable window. Active
rates around 1 to 5 trades per active day are allowed only when overlap, daily
caps, costs, drawdown, and monthly loss counts remain acceptable.

## Allowed Paths

- `docs/work_packets/WPR106-151-causal-multiday-level-retest-search.md`
- `docs/stage_reports/STAGE_R106_CAUSAL_MULTIDAY_LEVEL_RETEST_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_151_causal_multiday_level_retest_search/**`

## Inputs

- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/**`
- Rejection context from WPR106-126, WPR106-129, WPR106-130, and WPR106-150
  reports and artifacts.

May 2026 may be read only after fixed pre-May survivors are selected. No May
data may influence feature choice, filter choice, threshold, exit rule, ranking,
or selection.

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
- CUDA is not expected; report CPU/vectorized execution truthfully.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Reuse WPR106-126 source loading, period masks, cost accounting, and monthly
   stability metrics.
2. Build causal completed-level features for prior day, prior five trading
   days, and prior completed week.
3. Test breakout-follow, failed-break fade, retest rejection, retest momentum,
   and midline reversion variants with:
   - 96/384-bar normalization windows;
   - fixed 8/16/32-bar exits;
   - all/US sessions;
   - range-state and compression filters;
   - flow confirmation and contrarian filters;
   - both/long-only/short-only side modes;
   - target raw rates of 1, 3, and 5 signals/day;
   - explicit daily caps of 1 and 5 trades/day;
   - optional prior completed-month loss throttle.
4. Select only strict or loose pre-May survivors using WPR106 monthly-stability
   screens.
5. Replay May 2026 only for fixed pre-May survivors, seeding loss-throttle state
   with completed pre-May monthly returns.
6. Record whether the family remains rejected or whether a narrow research-only
   lead deserves deeper controls.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_151_causal_multiday_level_retest_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

## Evidence Results

- Evaluated rows: 113,400.
- Positive pre-May rows: 28,627.
- Positive annual-target rows: 3,850.
- Loose pre-May rows: 1,812.
- Strict pre-May rows: 1.
- Selected rows: 1 strict row.
- May benchmark: 0 positive rows, 1 negative row, 0 flat rows.
- Selected May return: -0.010441.

The only strict pre-May row was BTCUSDT prior-day breakout-follow, 96-bar
normalization, 32-bar hold, US session, compressed range-state, flow-confirmed,
long-only, target 5 raw signals/day, max 1 accepted trade/day, and no monthly
loss throttle. It had 120 pre-May trades, 28 active months, 4 losing months,
annual losses 2024: 1, 2025: 2, 2026 Jan-Apr: 1, +0.257106 pre-May net return,
-0.070493 max drawdown, 0.175802 best-month share, and 4/4 cost-stress
survival.

## Closeout

WPR106-151 rejects the causal multi-day level retest family as candidate-ready
or as a new promising lead. The packet found a legitimate strict pre-May
diagnostic row, but the fixed May benchmark lost -0.010441 across 3 trades.
Broader loose and annual-target diagnostics remain research-useful, especially
prior-day breakout-follow and ETHUSDT breakout/retest variants, but the May
holdout rejection prevents promotion.

No candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim exists.

Validation passed:

```powershell
python -m compileall -q data/research/wpr106_151_causal_multiday_level_retest_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts result: 460 passed.
