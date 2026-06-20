# WPR106-178 Pre-May Monthly Stability Selector

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the 2024-forward broad research search by testing whether a stricter
pre-May monthly stability selector can improve transfer from recent WPR106-176
and WPR106-177 search spaces. Prior packets found many positive pre-May rows
but repeatedly failed May 2026. This packet explicitly prioritizes
month-to-month stability, annual loss caps, active trade rates, cost stress,
and duplicate control before May/June replay.

## Scope

Selection/tuning source:

- WPR106-176 full pre-May ranking and monthly artifacts.
- WPR106-177 full pre-May ranking and monthly artifacts.
- Selection uses only 2024-01-01 through 2026-04-30 metrics/monthly rows.

Benchmark-only windows:

- May 2026 from WPR106-96 context.
- June 1-11 2026 from WPR106-168 packet-local verified Binance Vision daily
  archives, with WPR106-96 context through May used only as rolling-feature
  warmup.

Selector design:

- prefer rows with at most two losing months in 2024, at most two in 2025, and
  at most one in 2026 Jan-Apr;
- reward positive rolling 3-month and 6-month pre-May windows;
- penalize best-month concentration and dropout after removing top months;
- require active 1-5 trades/day behavior where available;
- deduplicate by pre-May behavior before final selection.

May and June must not be used for scoring, row inclusion, ranking, or
selection. June can only be replayed after fixed pre-May rows are selected.

The packet is artifact-only unless a blocking correctness issue is discovered.

## Allowed Paths

- `docs/work_packets/WPR106-178-pre-may-monthly-stability-selector.md`
- `docs/stage_reports/STAGE_R106_PRE_MAY_MONTHLY_STABILITY_SELECTOR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_178_pre_may_monthly_stability_selector/**`

## Plan

1. Load WPR106-176 and WPR106-177 full pre-May rankings and monthly-return
   artifacts.
2. Compute monthly stability diagnostics from pre-May rows only: annual loss
   counts, rolling 3/6-month minima, best-month concentration, top-month
   dropout return, active-month coverage, and active trade rates.
3. Select fixed rows using stability-first scoring and source/family/template
   exposure caps.
4. Replay fixed selected WPR106-176 rows with WPR106-176 helpers and WPR106-177
   rows with WPR106-177 helpers on pre-May, May 2026, and June 1-11 2026.
5. Write metrics, monthly/daily/trade, behavior-dedup, and May/June comparison
   artifacts.
6. Decide whether stability-first selection produces a candidate-ready lead or
   only diagnostics.
7. Write the report, ledger update, and validation notes.

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
python -m compileall -q data\research\wpr106_178_pre_may_monthly_stability_selector\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Completed as an artifact-only monthly stability selector over the WPR106-176
and WPR106-177 full pre-May universes. The selector scored 75,360 rows using
only 2024-01-01 through 2026-04-30 metrics/monthly evidence and found 2,016
stability-candidate rows. It selected 100 fixed rows: 49 from WPR106-176 and 51
from WPR106-177, with 5 strict rows and 95 stability rows.

The selected pre-May replay is cleaner than the prior loose selected sets:
97 rows are positive, 3 negative, median return is +0.967411, and active mean
is +0.958284. Deduplication still shows only 68 unique pre-May path hashes
across 100 selected rows.

May 2026 rejects the selected set: 24 rows are May-positive, 45 negative, 31
flat/no-trade, median return is 0.000000, and active mean is -0.015527. June
1-11 2026 is improved but not enough to offset May: 69 rows are positive, 31
negative, median +0.019182, and active mean +0.009868.

Only five selected rows satisfy the target annual loss caps of at most two
losing months in 2024, at most two in 2025, and at most one in 2026 Jan-Apr.
All five are from the already-rejected WPR106-176 ETHUSDT
`vol_breakout_follow` cluster, and their May mean return is -0.019544.

Decision: reject the monthly stability selector as candidate-ready,
portfolio-ready, or promotion-ready evidence. Useful diagnostics are BTCUSDT
WPR106-176 `vol_breakout_follow` with
`direct_flow_confirm_inverse_contra_skip`, and ETHUSDT WPR106-177
`cross_relative_reversion`, but neither supports a candidate claim.

Validation passed: scoped script compile, `src/tradingbotsuite` compile, and
contracts. Contracts reported 460 passed. No candidate pack, paper/live
artifact, order/sizing/runtime change, live config write, CUDA speedup claim,
or promotion claim exists.
