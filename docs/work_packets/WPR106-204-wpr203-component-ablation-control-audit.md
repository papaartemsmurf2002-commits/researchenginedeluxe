# WPR106-204 WPR203 Component Ablation Control Audit

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Objective

Audit the WPR106-203 cross-diagnostic component-portfolio lead before treating
it as more than a research-only diagnostic. WPR106-203 produced strict
pre-May portfolios with positive May benchmark behavior, but all strict rows
used the same WPR106-202 motif component. This packet tests whether the
apparent improvement survives source-only controls, leave-one-component-style
controls, parameter-neighborhood controls, and component-swap controls without
using May 2026 for tuning.

## Data And Selection Policy

- Input components are fixed WPR106-203 selected portfolio rows and WPR106-203
  component pools.
- Control construction and pre-May control evaluation use only 2024-01-01
  through 2026-04-30 UTC evidence.
- May 2026 is benchmark-only after the fixed control set is defined.
- Controls may replay active entry rates around 1 to 5 trades/day if overlap
  blocking, daily caps, costs, and monthly stability are explicit.
- All outputs are `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-204-wpr203-component-ablation-control-audit.md`
- `docs/stage_reports/STAGE_R106_WPR203_COMPONENT_ABLATION_CONTROL_AUDIT_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered
- `data/research/wpr106_204_wpr203_component_ablation_control_audit/**`

No source package, config, fixture, live, runtime, order-placement, sizing, or
promotion path is in scope.

## Planned Work

1. Create a packet-local runner that imports WPR106-203 replay helpers and
   reads WPR106-203 selected rows, component pools, and component trade
   artifacts.
2. Build deterministic pre-May control variants for the WPR106-203 selected
   rows: base replay, opening-only, motif-only, no-health, cap neighbors,
   priority neighbors, opening-weight neighborhoods, motif-component swaps,
   opening-component swaps, and bounded deterministic return-permutation
   controls for the highest-ranked parents.
3. Replay each fixed control on pre-May evidence with the WPR106-203 overlap,
   cost, daily-cap, and health-gate semantics.
4. Benchmark the same fixed controls on May 2026 only after the pre-May
   control universe exists.
5. Summarize whether WPR106-203 complementarity is robust or is mostly a
   post-selected single-motif concentration effect.
6. Document artifacts, interpretation, and validation.

## Research Boundary

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim. CUDA is not planned; if the runner is CPU/vectorized
only, the manifest must say so truthfully.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_204_wpr203_component_ablation_control_audit\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Closeout Evidence

The completed runner evaluated 2,922 fixed controls. All controls were positive
pre-May, with median pre-May return +0.790345, median active months 25, median
losing months 5, 1,803 annual-target rows, and 1,328 strict-like rows.

The WPR106-203 base replay reproduced 100/100 strict-like rows. Source-only
controls produced zero strict-like rows despite all 200 rows being positive.
Motif-component swaps produced zero strict-like rows across 900 positive
pre-May controls. Every strict-like row in the full WPR106-204 control universe
uses canonical motif component `motif202-00860ffdbf2eb058`; zero strict-like
rows use any alternate motif component.

May 2026 remained benchmark-only after the fixed control universe existed.
Across all controls, May had 2,771 positive rows, 115 negative rows, 36 flat
rows, median return +0.018368, and active mean +0.017089.

WPR106-204 keeps WPR106-203 alive as a research-only diagnostic component
portfolio because source-only controls do not reproduce the strict profile and
opening/parameter neighbors remain broad inside the canonical-motif
neighborhood. It does not make WPR106-203 candidate-ready because strict-like
behavior remains fully concentrated in one post-selected motif component and
bounded return-permutation controls leave exact motif timing unproven.

Final close validation passed:

```powershell
python -m compileall -q data\research\wpr106_204_wpr203_component_ablation_control_audit\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
