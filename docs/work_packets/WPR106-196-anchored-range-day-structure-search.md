# WPR106-196 Anchored Range Day-Structure Search

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Objective

Continue the WPR106 2024-forward broad strategy search with a fresh
artifact-only entry family that is not another defense of the rejected sparse
side-veto, KNN-veto, static portfolio, motif, flow-burst, or pair-spread
leads.

WPR106-196 tests causal completed-bar day-structure entries using prior-day
levels, opening ranges, rolling multi-day range location, intraday VWAP
residual, completed-bar flow, and volatility state. The intent is to give
old transparent breakout/fade ideas a fair modern-window variant while
ranking by month-to-month stability rather than one large profitable window.

## Data And Selection Policy

- Optimization, thresholding, row ranking, and selection use only
  2024-01-01 through 2026-04-30 UTC.
- May 2026 is benchmark-only after the fixed pre-May selected set exists.
- May 2026 must not influence template choice, threshold choice, state filter,
  side mode, hold, session, daily cap, row ranking, or row inclusion.
- The search may allow active 1, 3, and 5 raw signals per day when the replay
  applies realistic costs, overlap skipping, and accepted-trade daily caps.
- All outputs are `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-196-anchored-range-day-structure-search.md`
- `docs/stage_reports/STAGE_R106_ANCHORED_RANGE_DAY_STRUCTURE_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered
- `data/research/wpr106_196_anchored_range_day_structure_search/**`

No other source, config, fixture, live, runtime, order-placement, sizing, or
promotion path is in scope.

## Planned Work

1. Create a packet-local runner that imports the existing WPR106-170 helper
   module for aligned BTCUSDT/ETHUSDT source context, cost constants,
   completed-bar period masks, metrics, and artifact writing conventions.
2. Build causal day-structure features from completed bars:
   - shifted prior-day high, low, close, range, and return;
   - opening-range highs/lows after the opening window has completed;
   - current day high/low so far;
   - current day VWAP residual and day-open gap;
   - shifted rolling multi-day high/low/range location;
   - completed-bar return, flow, wick, volume, and volatility z-scores.
3. Evaluate anchored breakout, breakout-fade, gap-fill, opening-range,
   VWAP-reversion, weekly-range, and liquidity-sweep style templates across
   BTCUSDT and ETHUSDT with holds, sessions, side modes, target signal rates,
   state filters, and daily caps.
4. Select rows strictly from pre-May stability diagnostics, then replay the
   fixed selected set on May 2026 as a benchmark holdout.
5. Write ranking, monthly, selected replay, benchmark, comparison, logs, and
   JSON summary artifacts.
6. Update the stage report and ledger with the actual evidence.
7. Run the validation baseline.

## Research Boundary

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim. CUDA is not planned; if the runner is CPU/vectorized
only, the manifest must say so truthfully.

## Validation

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_196_anchored_range_day_structure_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.

## Exit Evidence

WPR106-196 evaluated 51,840 anchored range/day-structure rows. All feature
thresholds, state filters, hold/session/side/daily-cap choices, ranking, and
selection used 2024-01-01 through 2026-04-30; May 2026 was benchmark-only
after fixed pre-May selection.

The corrected final run used template-relevant anchor variants only, after an
initial unclosed run exposed duplicate prior-day/VWAP trade paths when every
template was repeated across every opening and rolling-range anchor. The
authoritative run found 8,900 positive pre-May rows, 1,458 annual-target rows,
85 loose rows, and zero strict rows.

The fixed selected set contains 100 ETHUSDT rows: 92
`positive_recent_stability` rows and eight `loose_recent` rows, with
72 `opening_range_breakout_follow` rows and 28 `prior_day_breakout_follow`
rows. Selected pre-May replay is 100 positive rows, zero negative rows,
median +0.856864, active mean +0.876398, best +1.196304, and worst
+0.597246.

May benchmark replay rejects the set: all 100 rows are active, but only 36 are
positive and 64 are negative, with median -0.007769, active mean -0.009575,
best +0.062069, and worst -0.052891.

The best May row is `day196-b707d26e4b8fa963`, an ETHUSDT
`opening_range_breakout_follow` short-only row with a 4-bar opening window,
32-bar hold, all session, all state filter, target 5 raw signals/day, and
daily cap 1. It records +1.006399 pre-May over 176 trades, 28 active months,
max drawdown -0.150763, and 100% cost-stress survival, then +0.062069 in May
over seven trades. It remains diagnostic only because it has 10 pre-May losing
months, including five in 2024 and four in 2025.

WPR106-196 rejects the anchored range/day-structure family as candidate-ready,
portfolio-ready, or promotion-ready. It preserves the ETHUSDT opening-range
short-follow pocket only as a research clue for a narrower stability/control
follow-up. No candidate pack, paper/live artifact, order/sizing/runtime
change, live configuration write, CUDA speedup claim, or promotion claim was
created. Focused script compile, compileall, and contracts validation passed.
