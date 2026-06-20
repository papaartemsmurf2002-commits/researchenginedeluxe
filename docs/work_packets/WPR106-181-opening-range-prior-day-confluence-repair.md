# WPR106-181 Opening-Range Prior-Day Confluence Repair

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the 2024-forward broad research search by revisiting two discarded
but structurally distinct families: WPR106-129 opening-range breakout/fade and
WPR106-130 prior-day level/gap behavior. WPR106-129 produced active profitable
pre-May diagnostics but every selected row lost in May. WPR106-130 found one
strict ETHUSDT prior-day breakout row, but that fixed row failed May.

This packet tests a May-blind confluence repair: opening-range signals are
only evaluated through prior-day high/low/close, overnight gap, session, flow,
and volatility context, with active 1-5 trades/day accepted when costs,
overlap, daily caps, and month stability are handled.

## Scope

Selection/tuning window:

- 2024-01-01 through 2026-04-30 UTC.

Benchmark-only windows:

- May 2026, replayed only after fixed pre-May selection.

Inputs:

- WPR106-96 BTCUSDT/ETHUSDT 15m bar context through May 2026 and 15m
  aggTrade-flow aggregation used by WPR106-126/WPR106-129/WPR106-130.
- WPR106-129 and WPR106-130 reports/artifacts as negative evidence, not as
  candidate claims.

Confluence families:

- opening-range breakout only when aligned with prior-day level breakout;
- opening-range failed breakout fade near prior-day high/low;
- opening-range retest continuation after prior-day level reclaim;
- overnight gap continuation and gap reversion only after opening-range
  confirmation;
- inside-opening-range fade conditioned on prior-day close/VWAP displacement.

May must not be used for feature definitions, threshold choices, filter
choices, exit choices, row inclusion, ranking, or selection.

The packet is artifact-only unless a blocking correctness issue is discovered.

## Allowed Paths

- `docs/work_packets/WPR106-181-opening-range-prior-day-confluence-repair.md`
- `docs/stage_reports/STAGE_R106_OPENING_RANGE_PRIOR_DAY_CONFLUENCE_REPAIR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_181_opening_range_prior_day_confluence_repair/**`

## Plan

1. Reuse WPR106-126 source-context loading, completed-bar alignment, cost, and
   metrics helpers.
2. Build point-in-time opening-range, prior-day high/low/close, overnight gap,
   session, flow, and volatility features from completed 15m bars.
3. Evaluate confluence score families over 2024-01-01 through 2026-04-30 only.
4. Select fixed rows by annual loss caps, active-month coverage, 1-5
   trades/day behavior, cost stress, drawdown, best-month concentration, and
   dropout robustness.
5. Replay fixed selected rows on May 2026 only.
6. Write ranking, monthly/daily/trade artifacts, summary, report, ledger
   update, and validation notes.

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
python -m compileall -q data\research\wpr106_181_opening_range_prior_day_confluence_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Closed on 2026-06-12. The runner evaluated 51,840 BTCUSDT/ETHUSDT
opening-range/prior-day confluence rows using only 2024-01-01 through
2026-04-30 for thresholding, filters, daily caps, ranking, and selection.

The repair improved the original WPR106-129 all-negative May result, but not
enough for a lead. It found 6,223 positive pre-May rows, 21 annual-target rows,
196 loose rows, and zero strict rows. The annual-target rows were all ETHUSDT
EU `or_gap_continuation` variants with 41 trades, so they were too sparse for
the requested active profile and did not qualify as loose or strict.

The fixed selected set had 100 positive pre-May rows, median +0.486439, and
active mean +0.407773. May 2026 rejected the fixed set with 13 positive rows,
87 negative rows, median -0.009593, active mean -0.009877, best +0.010523, and
worst -0.046390. The `dropout_repair` tier was 0 positive and 19 negative in
May.

Decision: WPR106-181 rejects the opening-range/prior-day confluence repair as
candidate-ready, portfolio-ready, or promotion-ready. All outputs remain
research-only, observe-only, and `promotion_ready: false`; no candidate pack,
paper/live artifact, order path, sizing change, runtime-mode change, live
configuration write, CUDA speedup claim, or promotion claim was produced.

Validation passed:

```powershell
python -m compileall -q data\research\wpr106_181_opening_range_prior_day_confluence_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contract result: 460 passed.
