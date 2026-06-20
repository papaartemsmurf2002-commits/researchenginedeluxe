# WPR106-173 Anti-Signal Entry/Exit Screen

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the 2024-forward broad research search after WPR106-172 rejected the
adaptive barrier entry/exit screen. Test whether the many negative or weak
transparent completed-bar entry families become stable when traded as explicit
opposite-side anti-signals, while keeping costs, overlap, daily caps, and May
2026 holdout handling intact.

This packet is not a defense of the rejected BTC sparse side-veto path. It is a
fresh source-level directionality audit over transparent trend, range,
breakout, wick, flow, and compression families.

## Scope

Default tuning/search window:

- 2024-01-01 00:00:00 UTC through 2026-04-30 23:59:59 UTC.

Benchmark holdout:

- 2026-05-01 through 2026-05-31 UTC.

May 2026 must not be used for feature choice, threshold choice, side-policy
choice, exit choice, daily-cap choice, ranking, filtering, or selection. It may
only be replayed after fixed pre-May rows are selected.

The packet is artifact-only unless a blocking correctness issue is discovered.

## Allowed Paths

- `docs/work_packets/WPR106-173-anti-signal-entry-exit-screen.md`
- `docs/stage_reports/STAGE_R106_ANTI_SIGNAL_ENTRY_EXIT_SCREEN_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_173_anti_signal_entry_exit_screen/**`

## Plan

1. Load WPR106-96 verified BTCUSDT/ETHUSDT 15m and 1m aggTrade source context.
2. Reuse the transparent completed-bar feature/score definitions from the
   WPR106-172 source screen, but make side policy explicit.
3. Evaluate opposite-side anti-signal entries for trend, range, volatility
   breakout, wick, flow, and compression templates.
4. Calibrate thresholds from pre-May only for 1, 3, and 5 raw signals per
   active day.
5. Test fixed-hold and conservative ATR barrier exits with stop-first same-bar
   collision handling.
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
python -m compileall -q data\research\wpr106_173_anti_signal_entry_exit_screen\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Completed as an artifact-only research packet. The runner evaluated 35,550
pre-May rows across BTCUSDT/ETHUSDT, seven completed-bar entry templates, two
normalization windows, all/US sessions, five regime filters, actual anti-signal
long/short/both side modes, 1/3/5 target raw signals per day, fixed 16/32/64
exits, conservative ATR barriers, and 1/3/5 accepted-trade daily caps. All
thresholds, filters, side policies, exits, caps, ranking, and selection used
only 2024-01-01 through 2026-04-30. May 2026 was benchmark-only after fixed
pre-May selection.

The grid found 4,618 positive pre-May rows, 166 annual-target rows, 209 loose
rows, and 14 strict rows. All strict rows are ETHUSDT `vol_breakout_follow`
opposite-side anti-signals with `barrier_h32_tp2_sl1` exits. The fixed selected
set contains 100 rows: 14 strict and 86 loose, with median +0.894432 pre-May
net return, best +1.899726, and worst +0.170107.

May 2026 rejected the selected set as candidate-ready evidence: 10 selected
rows were May-positive, 42 May-negative, and 48 May-flat because no fixed-filter
May trades occurred. Best May return was +0.037054, worst -0.073293, and
median 0.000000. The strict subset was worse: four strict rows were active in
May and all four were negative, with active strict May mean -0.030600.

No candidate pack, paper/live artifact, order/sizing/runtime change, live
config write, CUDA speedup claim, or promotion claim exists.

Validation passed: scoped script compile, `src/tradingbotsuite` compile, and
contracts. Contracts reported 460 passed.
