# WPR106-198 Opening-Range Short Behavior Confirmation

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Objective

Confirm or reject the WPR106-197 controlled-downside ETHUSDT opening-range
short repair without using May 2026 for tuning. WPR106-197 improved May
transfer, but it still relied on health gates that created many inactive
months. This packet tests whether a behavior-deduplicated, higher-active-
coverage subset remains stable and whether the health gate is more than an
inactivity filter.

## Data And Selection Policy

- Source candidate filtering, replay, behavior deduplication, ranking, and
  selected-row inclusion use only WPR106-197 pre-May evidence from
  2024-01-01 through 2026-04-30 UTC.
- May 2026 is benchmark-only after the fixed behavior-deduplicated selected
  set exists.
- May 2026 must not influence source-pool filters, behavior hash selection,
  active-month floors, health-gate controls, side controls, ranking, or
  selected-row inclusion.
- Active 1 to 5 raw signals/day remain acceptable when WPR106 costs, overlap,
  and daily caps are applied.
- All outputs are `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-198-opening-range-short-behavior-confirmation.md`
- `docs/stage_reports/STAGE_R106_OPENING_RANGE_SHORT_BEHAVIOR_CONFIRMATION_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered
- `data/research/wpr106_198_opening_range_short_behavior_confirmation/**`

No source package, config, fixture, live, runtime, order-placement, sizing, or
promotion path is in scope.

## Planned Work

1. Create a packet-local runner that imports WPR106-197 helper code and reads
   WPR106-197 pre-May ranking artifacts.
2. Build a pre-May-only source pool from WPR106-197 rows with meaningful
   activity, drawdown, cost-stress, and annual/monthly behavior.
3. Replay source-pool rows on pre-May only, compute exact accepted-trade path
   hashes, and deduplicate behavior before selecting rows.
4. Rank behavior representatives by active-month coverage, annual loss-month
   stability, drawdown, cost-stress survival, latest-four-month behavior,
   drop-best-month behavior, and return.
5. After fixed pre-May selection, replay May 2026 benchmark for the selected
   set only.
6. Run controls for selected rows:
   - no-health-gate ablation;
   - long-only control;
   - both-sided overlap diagnostic;
   - inverted health-gate control where applicable.
7. Write source-pool, behavior-deduped, selected replay, May benchmark,
   control, comparison, log, and summary artifacts.
8. Update the stage report and ledger, then run validation.

## Research Boundary

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim. CUDA is not planned; if the runner is CPU/vectorized
only, the manifest must say so truthfully.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_198_opening_range_short_behavior_confirmation\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Exit Evidence

WPR106-198 completed the behavior-deduplicated confirmation and control
packet. The source pool replayed 1,818 WPR106-197 ETHUSDT opening-range short
rows, behavior-deduped them to 1,011 exact accepted-trade representatives, and
selected a fixed 100-row pre-May set before any May 2026 benchmark was run.

The selected set was strong in-sample over 2024-01-01 through 2026-04-30:
100 positive rows, zero negative rows, median net return +0.736564, active
mean +0.720171, 19 annual-target rows, 96 loose rows, and zero strict rows.
May 2026 benchmark evidence did not confirm candidate readiness: 84 active
rows, 48 positive rows, 36 negative rows, 16 flat rows, median net return
0.000000, and active mean +0.008183.

Controls weakened the WPR106-197 health-gate explanation. The no-health
ablation had 100 May-active rows, 58 positive rows, zero flat rows, and May
median +0.004472, outperforming the selected health-gated set on May breadth
and median. The inverse-health diagnostic was also not dead, with 39
May-positive rows and May active mean +0.005811. Long-only controls remained
weak, preserving short-side asymmetry only as a diagnostic.

Four selected rows tied for best May return at +0.056746. The summary
representative `or198-76e752a4e51c7f11` has 20 active pre-May months, four
pre-May losing months, max drawdown -0.051303, Sortino +1.497782, and 100%
cost-stress survival, but it remains research-only because it relies on eight
inactive pre-May months and fails strict pre-May readiness.

WPR106-198 rejects the health-gated behavior-confirmation set as
candidate-ready, portfolio-ready, or promotion-ready. It preserves the
controlled-downside ETHUSDT opening-range short pocket as a research-only
diagnostic. No candidate pack, paper/live artifact, order/sizing/runtime
change, live config write, CUDA speedup claim, or promotion claim exists.

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_198_opening_range_short_behavior_confirmation\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
