# WPR106-203 Cross-Diagnostic Component Portfolio

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Objective

Test whether recent independent diagnostic components can complement each
other in a May-blind portfolio. WPR106-201 found active ETHUSDT opening-range
short repairs with too many losing months and mixed May transfer. WPR106-202
found ETHUSDT motif risk-throttle rows with strong May transfer but too many
pre-May losing months. This packet tests whether combining fixed pre-May
selected components can reduce monthly loss counts and drawdown without using
May 2026 for tuning.

## Data And Selection Policy

- Component sources are fixed WPR106-201 and WPR106-202 selected rows and
  trade artifacts, each selected by its own pre-May process.
- Component pool construction, behavior deduplication, portfolio generation,
  weighting, overlap policy, daily caps, health gates, ranking, and selected
  portfolio inclusion use only 2024-01-01 through 2026-04-30 UTC.
- May 2026 is benchmark-only after the fixed selected portfolio set exists.
- Active entry rates around 1 to 5 trades/day are allowed when portfolio-level
  overlap blocking, daily caps, costs, and monthly stability are explicit.
- All outputs are `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-203-cross-diagnostic-component-portfolio.md`
- `docs/stage_reports/STAGE_R106_CROSS_DIAGNOSTIC_COMPONENT_PORTFOLIO_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered
- `data/research/wpr106_203_cross_diagnostic_component_portfolio/**`

No source package, config, fixture, live, runtime, order-placement, sizing, or
promotion path is in scope.

## Planned Work

1. Create a packet-local runner that reads WPR106-201 and WPR106-202 selected
   metrics/trade artifacts.
2. Normalize trade rows across the opening-range and motif sources while
   preserving source candidate IDs, side, timestamps, costs, and net returns.
3. Build a May-blind behavior-deduped component pool using pre-May trades and
   pre-May metrics only.
4. Generate deterministic cross-diagnostic portfolios with component weights,
   same-symbol overlap blocking, portfolio-level daily caps, and causal
   prior-month health gates.
5. Rank portfolios on pre-May return, active months, annual loss-month counts,
   drawdown, cost-stress survival, best-month concentration, and trade density.
6. Replay the fixed selected portfolios on pre-May and May 2026, then write
   metrics, monthly/daily/trade artifacts, component pools, comparison tables,
   and a summary manifest.
7. Document whether cross-diagnostic composition repairs stability or whether
   the combined components remain unstable.
8. Update the stage report and ledger, then run validation.

## Research Boundary

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim. CUDA is not planned; if the runner is CPU/vectorized
only, the manifest must say so truthfully.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_203_cross_diagnostic_component_portfolio\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Closeout Evidence

The completed bounded run evaluated 3,600 May-blind pre-May component
portfolio rows from 10 opening-range components and 10 motif components. It
found 3,600 positive rows, 1,309 annual-target rows, 922 loose rows, and 116
strict rows. The fixed selected set contains 100 strict rows, median pre-May
return +0.812433, median active months 25, median losing months 4, and 100/100
annual-target rows.

May 2026 remained benchmark-only. The selected May benchmark has 100 active
rows, 100 positive rows, zero negative rows, median May return +0.018368, and
active mean May return +0.017915.

Best stability row `port203-9d00a85ae9eed7fc` records +0.763664 pre-May over
187 trades, 25 active months, two losing months, max drawdown -0.043528, 100%
cost-stress survival, annual loss-month counts of 0/1/1 for 2024/2025/2026
Jan-Apr, and +0.013304 in May over 8 trades.

WPR106-203 is a promising research-only component-portfolio diagnostic, but it
is not candidate-ready, portfolio-ready, paper/live-ready, or promotion-ready.
It needs source-level ablations, leave-one-component-out controls,
weight-neighborhood tests, negative controls, transparent baselines, and
candidate-pack gate materialization before any eligibility claim.

Final close validation passed:

```powershell
python -m compileall -q data\research\wpr106_203_cross_diagnostic_component_portfolio\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
