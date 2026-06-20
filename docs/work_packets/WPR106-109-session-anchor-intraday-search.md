# WPR106-109 Session Anchor Intraday Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test a fresh 2024-forward family based on session and daily anchor structure:
opening-range breakouts/fades, prior-day range reactions, Asia/Europe range
breakouts/fades, daily VWAP deviation, and session-transition momentum or
reversal. This packet should determine whether simple intraday anchor logic can
produce active, cost-positive, month-stable pre-May leads before May 2026 is
used as a benchmark holdout.

## Scope

- Use WPR106-96 verified BTCUSDT/ETHUSDT 2024-01 through 2026-05 local public
  archive context.
- Optimize family, anchor window, side logic, threshold, hold, symbol, session,
  volatility/filter settings, and ranking only on 2024-01-01 through
  2026-04-30.
- Keep May 2026 fully out of feature choice, threshold choice, family choice,
  exit/hold choice, ranking, filtering, and selection.
- Apply fixed pre-May settings unchanged to May 2026 only after a row is
  selected as a promising pre-May lead.
- Use completed 15m bars only; enter on the next 15m open; require pre-May
  selected trades to exit before 2026-05-01.
- Test both breakout/momentum and fade/reversal variants around anchors that
  are known at the signal time.
- Allow active 1 to 5 trades per active day after one-position overlap
  handling.
- Measure explicit taker commission 0.0432% per side plus conservative
  slippage/spread allowance, active-rate density, monthly returns, annual
  losing-month counts, drawdown, overlap skips, and cost-stress survival.
- Keep every artifact research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-109-session-anchor-intraday-search.md`
- `docs/stage_reports/STAGE_R106_SESSION_ANCHOR_INTRADAY_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_109*/**`

## Out of scope

- No May 2026 tuning, feature/filter feedback, threshold feedback, exit/hold
  feedback, optimizer feedback, or cost tuning.
- No source package changes unless a small, scoped, testable blocker prevents
  artifact-only research.
- No candidate pack, paper/live artifact, order placement, position sizing,
  runtime-mode change, live configuration write, CUDA speedup claim, or
  promotion claim.
- No synthetic fallback data.
- No fitted threshold or score that uses May labels, May returns, May quantiles,
  or May distributions.

## Exit evidence

- A deterministic WPR106-109 runner and pre-May search artifacts are written
  under `data/research/wpr106_109*/`.
- Pre-May selected rows, monthly returns, trades, and benchmark-only May rows
  are written separately when any promising pre-May row qualifies.
- The stage report records whether any row satisfies the target profile of
  roughly zero to two losing months per full pre-May year, whether active-rate
  behavior is acceptable, and whether May confirms or rejects fixed promising
  rows.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

## Closeout

Closed on 2026-06-11. The artifact runner
`data/research/wpr106_109_session_anchor_intraday_search/scripts/run_wpr106_109_session_anchor_search.py`
evaluated 9,600 BTCUSDT/ETHUSDT session-anchor rows over the WPR106-96 verified
2024-01 through 2026-05 public-archive context. Family, anchor-window, threshold,
hold, session/filter, ranking, and selection used only 2024-01-01 through
2026-04-30; May 2026 was joined only after pre-May selection as a benchmark
holdout.

The run found 1,436 positive pre-May rows, 150 loose pre-May rows, and 0 strict
month-stability rows. All positive rows were inside the allowed 1 to 5 trades
per active day after one-position overlap handling, so active-rate density was
not the blocker. The blocker was annual month stability: zero positive rows met
the full-year target of no more than two losing active months in both 2024 and
2025, and zero met the combined full-year plus partial-2026 target. The 150
fixed selected rows benchmarked in May with 19 positive, 118 negative, and 13
flat rows.

Main artifacts:

- `docs/stage_reports/STAGE_R106_SESSION_ANCHOR_INTRADAY_SEARCH_REPORT.md`
- `data/research/wpr106_109_session_anchor_intraday_search/wpr106_109_session_anchor_summary.json`
- `data/research/wpr106_109_session_anchor_intraday_search/pre_may/combined_ranking.parquet`
- `data/research/wpr106_109_session_anchor_intraday_search/pre_may/family_summary.parquet`
- `data/research/wpr106_109_session_anchor_intraday_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_109_session_anchor_intraday_search/may_benchmark/selected_may_benchmark_metrics.parquet`

Validation passed:

- `python -m compileall -q data/research/wpr106_109_session_anchor_intraday_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` reported 460 passed.

No candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim exists.
