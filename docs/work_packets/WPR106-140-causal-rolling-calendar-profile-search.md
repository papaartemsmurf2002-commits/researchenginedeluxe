# WPR106-140 Causal Rolling Calendar Profile Search

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Test whether the WPR106-139 calendar/session idea fails because full-window
pre-May calendar buckets overfit, or because time-bucket profiles are not a
durable edge. This packet replaces frozen full-window profiles with causal
rolling profiles that only use completed prior same-bucket outcomes, while
keeping May 2026 out of tuning and benchmarked only after fixed pre-May
selection.

## Allowed Paths

- `docs/work_packets/WPR106-140-causal-rolling-calendar-profile-search.md`
- `docs/stage_reports/STAGE_R106_CAUSAL_ROLLING_CALENDAR_PROFILE_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_140_causal_rolling_calendar_profile_search/**`

## Inputs

- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/features/**`
- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/scripts/run_wpr106_126_liquidity_sweep_wick_failure_search.py`
- `data/research/wpr106_139_calendar_session_interaction_search/**`

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, live configuration write, or promotion claim.
- All parameter choice, threshold choice, filter choice, ranking, and selection
  must use only 2024-01-01 through 2026-04-30.
- Rolling profile features must use completed prior labels only. A prior label
  is usable only when its fixed-hold exit timestamp is before the current
  signal timestamp.
- May 2026 profile history must be frozen to labels completed before
  2026-05-01, so no May label outcome can influence any May benchmark signal.
- May 2026 may be replayed only after fixed pre-May selected rows are written.
- Features must use completed bars only and next-bar entries.
- CUDA is not expected. CPU/vectorized pandas/accounting with bounded loops is
  sufficient and no speedup claim is allowed.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Load WPR106-96 verified 15m BTCUSDT/ETHUSDT contexts through May 2026.
2. Build rolling same-bucket profile means, t-stat-like scores, directions, and
   strengths over lookbacks of recent completed labels.
3. Search profile-follow, profile-pullback, profile-momentum,
   flow-confirmed-profile, and volatility-profile variants across bucket modes,
   fixed holds, rolling lookbacks, session filters, volatility filters, flow
   filters, and active target rates of 1/3/5 signals per day.
4. Use only pre-May data to calibrate thresholds and rank rows.
5. Select strict rows first; if none exist, select loose rows. Then benchmark
   May 2026 separately with the fixed params and frozen pre-May profile
   history.
6. Report whether causal rolling profiles reduce WPR106-139's May failure.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_140_causal_rolling_calendar_profile_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed:

- `python -m compileall -q data/research/wpr106_140_causal_rolling_calendar_profile_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed.

## Closeout

WPR106-140 is rejected as a candidate lead. The causal rolling profile search
evaluated 34,560 pre-May rows and found 3,257 positive rows, 115 annual-target
rows, 84 loose rows, and zero strict rows. Because there were no strict rows,
the fixed benchmark set used the 84 loose rows. May 2026 was benchmark-only
with profile history frozen to labels completed before 2026-05-01; the fixed
loose set produced 12 May-positive rows, 58 May-negative rows, and 14 flat rows,
with median May net return -0.014084. No candidate pack, paper/live artifact,
order/sizing/runtime change, live configuration write, CUDA speedup claim, or
promotion claim was created.
