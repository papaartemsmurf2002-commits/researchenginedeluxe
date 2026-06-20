# WPR106-205 Canonical Motif Timing Falsification

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Objective

Falsify the canonical motif dependence found by WPR106-204 before the
WPR106-203 component-portfolio lead is treated as more than a research-only
diagnostic. WPR106-204 showed that every strict-like control depends on
`motif202-00860ffdbf2eb058`. This packet tests whether that dependence is
specific to the canonical motif trade timing and return sequence, or whether
simple artifact-level perturbations preserve the apparent stability.

## Data And Selection Policy

- Input parents are the fixed WPR106-203 selected portfolios.
- Input component trades are fixed WPR106-201 opening trades and WPR106-202
  canonical motif trades used by WPR106-203.
- Control construction and pre-May evaluation use only 2024-01-01 through
  2026-04-30 UTC evidence.
- May 2026 is benchmark-only after the fixed control universe exists.
- Controls are artifact-level falsification tests; they do not recompute fresh
  market labels from shifted entries.
- All outputs are `research_only`, `observe_only`, `control_only`, and
  `promotion_ready: false`.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-205-canonical-motif-timing-falsification.md`
- `docs/stage_reports/STAGE_R106_CANONICAL_MOTIF_TIMING_FALSIFICATION_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered
- `data/research/wpr106_205_canonical_motif_timing_falsification/**`

No source package, config, fixture, live, runtime, order-placement, sizing, or
promotion path is in scope.

## Planned Work

1. Create a packet-local runner that imports WPR106-203 replay helpers and
   reads WPR106-203 selected parents plus WPR106-201/WPR106-202 component
   trades.
2. Build deterministic controls for all 100 selected parents: base replay,
   motif return shuffles, motif return rotations, motif zero-return baseline,
   motif constant-return baselines, motif sign-flip baseline, opening-return
   shuffle contrast controls, and motif timestamp shifts.
3. Replay each fixed control on pre-May evidence with WPR106-203 overlap,
   daily-cap, cost, and health-gate semantics.
4. Benchmark the same fixed controls on May 2026 only after the pre-May
   control universe exists.
5. Summarize whether strict-like stability collapses under timing/return
   perturbations or remains too easy to reproduce from artifact-level return
   distributions.
6. Document artifacts, interpretation, and validation.

## Research Boundary

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim. CUDA is not planned; if the runner is CPU/vectorized
only, the manifest must say so truthfully.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_205_canonical_motif_timing_falsification\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Closeout Evidence

The completed runner evaluated 2,200 fixed artifact-level controls over the
100 WPR106-203 selected parents. May 2026 remained benchmark-only.

Base replay reproduced 100/100 strict-like rows. Non-base controls produced
1,110 strict-like rows: 310/500 motif-return shuffles, 152/300 motif-return
rotations, 440/600 motif timestamp shifts, and 200/200 motif constant-return
baselines were strict-like. The motif zero-return baseline dropped to 8/100
strict-like rows, motif sign-flip dropped to 0/100 strict-like rows, and
opening-return shuffle controls dropped to 0/300 strict-like rows.

This rejects a timing-specific or exact-return-sequence claim for the canonical
motif portfolio pocket at the artifact level. The canonical motif return
contribution matters, but constant, shuffled, shifted, and rotated controls
preserve strict-like stability too often. WPR106-203/WPR106-204 remains
research-only diagnostic evidence, not a candidate-ready or portfolio-ready
lead.

Final close validation passed:

```powershell
python -m compileall -q data\research\wpr106_205_canonical_motif_timing_falsification\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
