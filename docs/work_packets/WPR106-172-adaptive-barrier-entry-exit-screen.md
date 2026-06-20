# WPR106-172 Adaptive Barrier Entry/Exit Screen

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the 2024-forward broad research search after WPR106-171 rejected the
market-state regime-gated intrabar-flow repair. Test a fresh source strategy
screen that combines transparent completed-bar entry families with conservative
fixed-hold and ATR barrier exits, instead of repairing prior selected trade
ledgers.

This packet revisits old trend, range, breakout, wick, and flow families in a
new entry/exit formulation. Active rates up to five accepted trades per day are
allowed when source overlap, daily caps, costs, and path ambiguity are handled
explicitly. Ranking targets month-to-month stability rather than one large
profitable window.

## Scope

Default tuning/search window:

- 2024-01-01 00:00:00 UTC through 2026-04-30 23:59:59 UTC.

Benchmark holdout:

- 2026-05-01 through 2026-05-31 UTC.

May 2026 must not be used for feature choice, threshold choice, exit choice,
daily-cap choice, ranking, filtering, or selection. It may only be replayed
after fixed pre-May rows are selected.

The packet is artifact-only unless a blocking correctness issue is discovered.

## Allowed Paths

- `docs/work_packets/WPR106-172-adaptive-barrier-entry-exit-screen.md`
- `docs/stage_reports/STAGE_R106_ADAPTIVE_BARRIER_ENTRY_EXIT_SCREEN_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_172_adaptive_barrier_entry_exit_screen/**`

## Plan

1. Load WPR106-96 verified BTCUSDT/ETHUSDT 15m and 1m aggTrade source context.
2. Build completed-bar feature caches for trend, range, breakout, wick, flow,
   session, volatility, and cross-symbol state without May-driven thresholds.
3. Generate transparent entry scores across trend pullback, range reversion,
   volatility breakout, wick/sweep reversal, and flow divergence families.
4. Calibrate entry thresholds from pre-May only for 1, 3, and 5 raw signals per
   active day.
5. Evaluate fixed-hold exits and conservative ATR stop/target exits. If both a
   stop and target are hit in the same bar, count the stop first.
6. Enforce one-position overlap handling and accepted-trade daily caps of 1, 3,
   and 5.
7. Rank only on pre-May monthly stability, annual losing-month profile,
   drawdown, cost stress, trade count, active rate, overlap, and concentration.
8. Replay only fixed promising/loose pre-May rows on May 2026 as a benchmark.
9. Write research-only artifacts, report, ledger update, and validation notes.

## Research Boundary

All outputs remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_172_adaptive_barrier_entry_exit_screen\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Completed as an artifact-only research packet. After a bounded runtime
narrowing, the runner evaluated 35,550 pre-May rows across BTCUSDT/ETHUSDT,
seven completed-bar entry templates, two normalization windows, all/US
sessions, five regime filters, three side modes, 1/3/5 target raw signals per
day, fixed 16/32/64 exits, conservative ATR barriers, and 1/3/5 accepted-trade
daily caps. All thresholds, filters, exits, caps, ranking, and selection used
only 2024-01-01 through 2026-04-30. May 2026 was benchmark-only after fixed
pre-May selection.

The grid found 5,072 positive pre-May rows, 190 annual-target rows, 71 loose
rows, and zero strict rows. The 71 selected rows are all loose, with median
+0.319864 pre-May net return, best +1.114763, and worst +0.057242.

May 2026 rejected the selected set as candidate-ready evidence: 5 rows were
May-positive, 10 May-negative, and 56 May-flat because no fixed-filter May
trades occurred. Best May return was +0.022584, worst -0.074505, and median
0.000000. Among the 15 active May rows, mean return was -0.012550. The best
diagnostic pocket is ETHUSDT volatility-breakout with flow-confirm filtering
and fixed 64-bar exits, but it is not candidate-ready because no strict pre-May
row exists and May activity is sparse/negative on average.

No candidate pack, paper/live artifact, order/sizing/runtime change, live
config write, CUDA speedup claim, or promotion claim exists.

Validation passed: scoped script compile, `src/tradingbotsuite` compile, and
contracts. Contracts reported 460 passed.
