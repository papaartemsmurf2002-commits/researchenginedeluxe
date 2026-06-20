# WPR106-139 Calendar Session Interaction Search

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Test a fresh artifact-only calendar/session interaction family over 2024-forward
BTCUSDT and ETHUSDT data. This packet moves away from defending rejected
KNN-veto/portfolio rows and tests whether completed-bar time-of-week,
session-phase, prior-session behavior, and flow/volatility context can create
active, month-stable 1-5 trades/day strategies.

## Allowed Paths

- `docs/work_packets/WPR106-139-calendar-session-interaction-search.md`
- `docs/stage_reports/STAGE_R106_CALENDAR_SESSION_INTERACTION_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_139_calendar_session_interaction_search/**`

## Inputs

- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/features/**`
- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/scripts/run_wpr106_126_liquidity_sweep_wick_failure_search.py`

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, live configuration write, or promotion claim.
- All feature construction, template choice, threshold choice, filter choice,
  ranking, and selection must use only 2024-01-01 through 2026-04-30.
- May 2026 may be replayed only after fixed pre-May selected rows are written.
- Features must use completed bars only and next-bar entries.
- CUDA is not expected. CPU/vectorized pandas accounting is sufficient and no
  speedup claim is allowed.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Load WPR106-96 verified 15m BTCUSDT/ETHUSDT feature contexts through May
   2026.
2. Build completed-bar calendar/session interaction scores from day-of-week,
   hour/session phase, prior-session returns/ranges, rolling volatility,
   volume, and aggTrade-flow proxies where present.
3. Search template variants for session-continuation, session-fade,
   day-of-week conditional breakout/fade, prior-session reversal, and
   flow-confirmed calendar impulse across fixed 4/8/16/32-bar holds.
4. Use pre-May-only quantile thresholds and filters, allowing active rates of
   1-5 trades/day when costs and overlap are handled.
5. Select strict rows first, loose rows only if strict is empty, then benchmark
   May 2026 separately after fixed selection.
6. Report monthly stability, annual losing-month counts, drawdown, best-month
   concentration, cost-stress survival, and May benchmark distribution.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_139_calendar_session_interaction_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed:

- `python -m compileall -q data/research/wpr106_139_calendar_session_interaction_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

## Closeout

Closed as a rejected research lead. The run evaluated 29,184 pre-May
calendar/session interaction rows across BTCUSDT and ETHUSDT, bucket modes
`session4`, `weekday_session4`, `hour`, and `weekday_hour`, fixed holds of
4/8/16/32 bars, session/volatility/flow filters, and active target rates of
1/3/5 signals per day. It found 9,735 positive pre-May rows, 237 annual-target
rows, 808 loose rows, and 17 strict rows. The fixed strict selection contained
17 rows.

The top selected row was ETHUSDT `flow_confirmed_calendar_impulse` with a
weekday-hour profile, 32-bar hold, high-volume filter, 678 trades, 486 active
days, 1.395062 trades per active day, 28 active months, 4 losing months,
annual losses of 2024: 2, 2025: 1, 2026 Jan-Apr: 1, +2.480657 pre-May net
return, -0.205831 max drawdown, 0.125698 best-month share, and full
cost-stress survival.

May 2026 rejected every fixed strict row: 0 positive, 17 negative, and 0 flat
selected rows. Best May was -0.000748, worst May was -0.133646, and median May
was -0.033021. No candidate pack, paper/live artifact, order/sizing/runtime
change, live configuration write, CUDA speedup claim, or promotion claim
exists.
