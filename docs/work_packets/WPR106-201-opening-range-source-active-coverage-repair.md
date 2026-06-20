# WPR106-201 Opening-Range Source Active-Coverage Repair

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Objective

Audit the WPR106-197 opening-range source-only diagnostic isolated by
WPR106-200, with the specific question: can the profitable ETHUSDT
opening-range short behavior be repaired into a more active and month-stable
research lead without using May 2026 for tuning?

WPR106-200 found that the WPR106-199 strict-tier pocket was not explained by
KNN/non-opening complementarity. The best diagnostic source was
`WPR106-197:or197-aaf5acc56f96eddc`, which had strong pre-May return,
three pre-May losing months, and a positive May benchmark, but was inactive in
nine pre-May months and lacked independent source-level ablation, baseline,
and stability-region evidence.

## Data And Selection Policy

- Optimization, source ranking, selection, thresholds, filters, health gates,
  and interpretation use only 2024-01-01 through 2026-04-30 UTC.
- May 2026 remains fully out of tuning and is used only as a benchmark after
  the fixed pre-May selected set exists.
- The runner may reuse WPR106-197/WPR106-196 packet-local helper functions and
  cost accounting so the comparison stays tied to the source diagnostic.
- Selection should prefer active coverage, month-to-month stability, downside
  control, and cost-stress survival over one large profitable window.
- Normal active entry rates of roughly one to five entries per day are allowed
  when overlap blocking, daily caps, and costs are explicit.
- All outputs are `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-201-opening-range-source-active-coverage-repair.md`
- `docs/stage_reports/STAGE_R106_OPENING_RANGE_SOURCE_ACTIVE_COVERAGE_REPAIR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered
- `data/research/wpr106_201_opening_range_source_active_coverage_repair/**`

No source package, config, fixture, live, runtime, order-placement, sizing, or
promotion path is in scope.

## Planned Work

1. Create a packet-local runner that imports WPR106-197 helpers and reuses the
   WPR106-196/WPR106-170 ETHUSDT opening-range context, feature, label, cost,
   overlap, daily-cap, monthly, drawdown, Sortino, and cost-stress accounting.
2. Run a May-blind active-coverage sweep around the WPR106-197 source pocket,
   including nearby opening windows, holds, state filters, target raw signal
   rates, threshold multipliers, daily caps, and causal prior-month health
   gates.
3. Add packet-local causal monthly gates only if needed for fair repair, with
   every gate based solely on prior pre-May monthly history.
4. Rank candidates on pre-May evidence using active months, inactivity,
   losing-month counts by year, latest-month behavior, rolling stability,
   drawdown, cost-stress survival, best-month concentration, and total return.
5. Replay the fixed selected set on pre-May and May 2026, then write metrics,
   monthly/daily/trade artifacts, ranking files, selection comparison, and a
   summary manifest.
6. Generate simple source-level controls for selected rows, including no
   health gate, no state filter where meaningful, lower/higher threshold
   neighbors, and long/both-side controls.
7. Document whether any row reaches active-coverage/stability plausibility or
   whether the WPR106-197 source pocket remains too sparse or concentrated.
8. Update the stage report and ledger, then run validation.

## Research Boundary

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim. CUDA is not planned; any CPU/vectorized-only runner
must state that truthfully.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_201_opening_range_source_active_coverage_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Exit Evidence

WPR106-201 completed the opening-range source active-coverage repair audit. It
evaluated 21,600 ETHUSDT opening-range short rows around the WPR106-197 source
pocket using only 2024-01-01 through 2026-04-30 for search, ranking, and
selection. May 2026 was benchmark-only after the fixed selected set existed.

The search found 17,472 positive pre-May rows, 3,535 annual-target rows, 3,496
rows with at least 24 active pre-May months, 1,030 loose rows, and zero strict
rows. No positive row combined at least 24 active months with the annual
loss-month target.

The fixed selected set contains 100 rows, all positive pre-May, with median
pre-May return +0.714290, median active months 22, median inactive months 6,
median losing months 6, zero strict rows, and one annual-target row. May
benchmark is mixed: 75 active rows, 43 positive, 32 negative, 25 flat, median
May return 0.000000, active mean +0.000878, best +0.023197, and worst
-0.026205.

The best active-coverage controlled-downside repair,
`or201-ce81f63d6911db8b`, records +0.899985 pre-May over 106 trades, all 28
pre-May months active, six losing months, max drawdown -0.073481, and 100%
cost-stress survival, but benchmarks -0.003969 in May over three trades. The
two rows that reached at least 24 active months and five or fewer losing
months also benchmarked -0.003969 in May.

The two WPR106-197 reference anchors,
`or197-aaf5acc56f96eddc` and `or197-f37732bbc7bd4db6`, remain profitable but
sparse: median +0.958549 pre-May, median 19 active months, median nine
inactive months, median 3.5 losing months, and median May +0.050189.

WPR106-201 rejects the active-coverage repair as candidate-ready,
portfolio-ready, or promotion-ready. It preserves the opening-range short
source pocket as a research-only diagnostic, but the active repair trades away
the desired monthly stability and does not produce convincing May transfer.
No candidate pack, paper/live artifact, order/sizing/runtime change, live
config write, CUDA speedup claim, or promotion claim exists.

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_201_opening_range_source_active_coverage_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
