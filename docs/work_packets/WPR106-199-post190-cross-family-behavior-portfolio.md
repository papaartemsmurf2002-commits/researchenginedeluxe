# WPR106-199 Post-190 Cross-Family Behavior Portfolio Search

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Objective

Move beyond the rejected WPR106-198 opening-range health-gate repair by testing
whether recent post-190 diagnostic families can combine into more stable,
overlap-aware portfolios. This packet revisits discarded and diagnostic
families from WPR106-190 through WPR106-198, deduplicates exact accepted-trade
behavior, builds complementary portfolios using only pre-May evidence, and
uses May 2026 only as a benchmark holdout for the fixed selected set.

The target remains broad 2024-forward research: prefer month-to-month
stability, tolerate active 1 to 5 trades/day when costs and overlap are
handled, and reject families only after controls make the failure explicit.

## Data And Selection Policy

- Source loading, source filtering, behavior deduplication, portfolio
  construction, ranking, selected-row inclusion, and all thresholds use only
  2024-01-01 through 2026-04-30 UTC evidence from existing packet artifacts.
- May 2026 is benchmark-only after the fixed selected portfolio set exists.
- May 2026 must not influence source-pool filters, complement scoring,
  portfolio composition, daily-cap choice, ranking, or selected-row inclusion.
- Existing source trades already include their packet-local cost accounting;
  this packet reweights source trade gross/cost/net returns by portfolio member
  count and applies same-symbol overlap and portfolio-level daily caps.
- All outputs are `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-199-post190-cross-family-behavior-portfolio.md`
- `docs/stage_reports/STAGE_R106_POST190_CROSS_FAMILY_BEHAVIOR_PORTFOLIO_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered
- `data/research/wpr106_199_post190_cross_family_behavior_portfolio/**`

No source package, config, fixture, live, runtime, order-placement, sizing, or
promotion path is in scope.

## Planned Work

1. Create a packet-local runner that reads existing selected pre-May and May
   trade/metric artifacts from WPR106-190 through WPR106-198 when available.
2. Normalize source rows with stable packet-qualified source IDs and exact
   accepted-trade path hashes.
3. Build a May-blind source pool from positive, sufficiently active pre-May
   source rows, then behavior-deduplicate by exact trade path.
4. Generate two-, three-, and four-member portfolios using quality,
   loss-complement, low-correlation, packet-diverse, and stability-rescue
   complement scorers.
5. Evaluate portfolios on pre-May evidence with same-symbol overlap blocking,
   member-count return weighting, portfolio-level daily caps, monthly
   diagnostics, cost stress, drawdown, and Sortino.
6. Select a fixed pre-May set by strict/loose/positive-stability tiers with
   caps that prevent one packet or one portfolio mode from dominating.
7. Replay only the fixed selected set on May 2026 and write comparison
   artifacts.
8. Write summary, report, ledger update, and run validation.

## Research Boundary

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim. CUDA is not planned; if the runner is CPU/vectorized
only, the manifest must say so truthfully.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_199_post190_cross_family_behavior_portfolio\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Exit Evidence

WPR106-199 completed the post-190 cross-family behavior portfolio search. The
final authoritative runner loads selected trade/metric artifacts from WPR106-190
through WPR106-198, normalizes mixed side/timestamp schemas, behavior-dedupes
source rows by exact accepted-trade path, forces top-per-packet source seeds,
and applies pre-May-only source packet/source ID caps before selected May
benchmarking.

The source library contains 786 selected source metric rows and 422 exact
behavior-deduped source representatives. The generated portfolio funnel
evaluates 903 pre-May portfolio rows, all positive, including 53 annual-target
rows, 575 loose rows, and 53 strict rows. The fixed selected set contains 38
rows: 10 strict, 20 loose, and eight positive-stability rows.

Selected pre-May replay is strong in-sample: 38 active rows, 38 positive rows,
zero negative rows, median net return +0.623546, active mean +0.619484, best
+0.826019, and worst +0.390723. May 2026 benchmark rejects the selected set
overall: 38 active rows, 13 positive rows, 25 negative rows, median net return
-0.006735, active mean -0.006911, best +0.014893, and worst -0.034259.

The strict tier remains a research diagnostic: 10 rows, seven May-positive,
three May-negative, May median +0.006134, and median pre-May losing months
4.5. The best strict rows combine WPR106-196 anchored/opening-range behavior,
WPR106-197 opening-range short controls, and one WPR106-190 or WPR106-191 KNN
source. This is not candidate-ready because the full selected set fails May,
source concentration remains material, and independent source ablation,
transparent baselines, stability-region evidence, and candidate-pack gates are
missing.

WPR106-199 rejects the broad post-190 cross-family portfolio set as
candidate-ready, portfolio-ready, or promotion-ready. It preserves strict
low-correlation portfolios mixing WPR106-196/WPR106-197 with KNN sources as a
research-only follow-up diagnostic. No candidate pack, paper/live artifact,
order/sizing/runtime change, live config write, CUDA speedup claim, or
promotion claim exists.

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_199_post190_cross_family_behavior_portfolio\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
