# WPR106-197 Opening-Range Short Stability Control

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Objective

Follow up the WPR106-196 diagnostic without accepting it as a candidate. The
best WPR106-196 May row was an ETHUSDT opening-range-breakout short that
transferred to May 2026, but it had 10 pre-May losing months, including five
in 2024 and four in 2025. This packet tests whether the clue can be repaired
with May-blind stability controls rather than with post-hoc May tuning.

## Data And Selection Policy

- Optimization, thresholding, health-gate construction, row ranking, and
  selection use only 2024-01-01 through 2026-04-30 UTC.
- May 2026 is benchmark-only after the fixed pre-May selected set exists.
- May 2026 must not influence opening-window choice, hold, threshold,
  threshold multiplier, state filter, monthly health gate, session, daily cap,
  ranking, or selection.
- Active 1 to 5 raw signals/day remain allowed when overlap, daily caps, and
  WPR106 costs are applied.
- All outputs are `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-197-opening-range-short-stability-control.md`
- `docs/stage_reports/STAGE_R106_OPENING_RANGE_SHORT_STABILITY_CONTROL_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered
- `data/research/wpr106_197_opening_range_short_stability_control/**`

No source package, config, fixture, live, runtime, order-placement, sizing, or
promotion path is in scope.

## Planned Work

1. Create a packet-local runner that imports WPR106-196/WPR106-170 helper code
   for aligned source context, anchored opening-range features, costs,
   fixed-hold labels, overlap handling, daily caps, and metrics.
2. Restrict the entry family to ETHUSDT `opening_range_breakout_follow`
   short-only behavior and test meaningful May-blind variants:
   - opening windows of 4, 8, and 16 completed 15m bars;
   - 16, 24, 32, and 48 bar fixed holds;
   - all, EU, and US sessions;
   - bearish flow/trend/VWAP/range state filters;
   - raw signal targets between 1 and 5/day;
   - pre-May threshold multipliers;
   - prior-month and rolling prior-month health gates.
3. Apply health gates causally: a month may only be enabled from prior-month
   or prior-rolling-month behavior, never from its own return or future
   months. May 2026 health-gate state must be computed only from pre-May
   history.
4. Write pre-May ranking, selected replay, May benchmark, control rows, logs,
   and summary artifacts.
5. Reject or preserve the family based on month-to-month stability and May
   benchmark evidence, with controls against long/both-sided variants.
6. Update the stage report and ledger, then run validation.

## Research Boundary

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim. CUDA is not planned; if the runner is CPU/vectorized
only, the manifest must say so truthfully.

## Validation

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_197_opening_range_short_stability_control\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.

## Exit Evidence

WPR106-197 evaluated 138,240 ETHUSDT opening-range short stability-control
rows. All opening-window, hold, threshold, threshold-multiplier, state-filter,
health-gate, session, daily-cap, ranking, and selection choices used
2024-01-01 through 2026-04-30; May 2026 was benchmark-only after fixed
pre-May selection.

The screen found 73,904 positive pre-May rows, 28,568 annual-target rows,
1,966 loose rows, and zero strict rows. The fixed selected set contains
100 `annual_target_control` rows, with 79 `prev_month_positive` and 21
`rolling_3_loss_count_le1` health gates.

Selected pre-May replay is 100 positive rows, zero negative rows, median
+0.847369, active mean +0.845733, best +1.105636, and worst +0.726895.
May benchmark is a meaningful improvement over WPR106-196: 62 active rows,
55 positive rows, 7 negative rows, 38 flat rows, median +0.004472, active
mean +0.023551, best +0.055974, and worst -0.006421.

The best May row is `or197-bc838835e95dc29d`, an ETHUSDT opening-range short
with a 4-bar opening window, 32-bar hold, all session, controlled-downside
extension filter, target 3 raw signals/day, 1.30 threshold multiplier, daily
cap 3, and `prev_month_positive` health gate. It records +0.787461 pre-May
over 73 trades, 16 active months, 12 inactive months, three losing active
months, max drawdown -0.073845, Sortino +1.157944, and 100% cost-stress
survival, then +0.055974 in May over six trades.

Side controls show weak long-only behavior but overlapping both-sided behavior:
long controls have pre-May median -0.027666 and May mean -0.000273, while
both-sided controls have pre-May median +0.791980 and May median +0.004472
because they inherit most selected short trades.

WPR106-197 is promising research evidence, but it remains rejected as
candidate-ready, portfolio-ready, or promotion-ready because there are zero
strict rows, selected rows rely on health gates that create many inactive
months, the best May row has only 16 active pre-May months, and annual-target
rows are often sparse. No candidate pack, paper/live artifact, order/sizing/
runtime change, live configuration write, CUDA speedup claim, or promotion
claim was created. Focused script compile, compileall, and contracts
validation passed.
