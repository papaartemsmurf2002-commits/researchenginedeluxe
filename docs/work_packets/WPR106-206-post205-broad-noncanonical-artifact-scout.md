# WPR106-206 Post-205 Broad Noncanonical Artifact Scout

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Objective

Restart the broad 2024-forward search after WPR106-205 demoted the
WPR106-203/WPR106-204 canonical motif portfolio pocket. This packet scans
existing selected trade artifacts across prior WPR106 families, excluding
WPR106-203 through WPR106-205 controls and the falsified canonical motif row
`motif202-00860ffdbf2eb058`, to identify any noncanonical standalone source
rows that still show the requested month-to-month stability profile before
spending more compute on a deeper family-specific packet.

## Data And Selection Policy

- Source rows come only from existing WPR106 selected pre-May trade artifacts
  and matching May benchmark trade artifacts.
- Pre-May ranking, behavior deduplication, source-family summaries, and
  selected-row inclusion use only 2024-01-01 through 2026-04-30 UTC evidence.
- May 2026 is benchmark-only after the fixed selected set exists.
- The scout accepts active rates around 1 to 5 trades/day when overlap, daily
  counts, costs, and monthly stability are explicit in the source artifacts.
- All outputs are `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-206-post205-broad-noncanonical-artifact-scout.md`
- `docs/stage_reports/STAGE_R106_POST205_BROAD_NONCANONICAL_ARTIFACT_SCOUT_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered
- `data/research/wpr106_206_post205_broad_noncanonical_artifact_scout/**`

No source package, config, fixture, live, runtime, order-placement, sizing, or
promotion path is in scope.

## Planned Work

1. Create a packet-local runner that discovers WPR106 selected pre-May metrics
   and trade artifacts with matching May benchmark trades.
2. Exclude WPR106-203 through WPR106-205 controls, control-only rows, and
   canonical motif ID `motif202-00860ffdbf2eb058`.
3. Normalize trade rows across artifact schemas and recompute comparable
   pre-May metrics from trade evidence.
4. Behavior-deduplicate rows by accepted trade timing/side/return signature
   and rank them only on pre-May return, active months, annual loss counts,
   drawdown, best-month concentration, cost stress, and trade density.
5. Select a fixed pre-May noncanonical scout set, then benchmark that fixed set
   on May 2026.
6. Summarize broad family coverage and whether any noncanonical source row
   deserves deeper fresh strategy recomputation.
7. Document artifacts, interpretation, and validation.

## Research Boundary

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim. CUDA is not planned; if the runner is CPU/vectorized
only, the manifest must say so truthfully.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_206_post205_broad_noncanonical_artifact_scout\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Closeout Evidence

The completed runner loaded 68 source artifact directories and 4,133 source
rows, excluded WPR106-203 through WPR106-205 plus canonical motif row
`motif202-00860ffdbf2eb058`, and behavior-deduped to 2,604 noncanonical
pre-May rows. All 2,604 rows were positive pre-May, with 157 annual-target
rows and 45 strict-like rows.

The fixed selected set contains 150 rows: 45 strict noncanonical source rows,
8 annual-target source rows, and 97 positive active source rows. Median
selected pre-May return is +1.204596 with median active months 28 and median
losing months 5.

May 2026 remained benchmark-only. It rejects the selected set: 22 positive
rows, 107 negative rows, 21 flat rows, median May return -0.018163, and active
mean May return -0.034232.

The strongest pre-May rows come from WPR106-139 calendar/session artifacts but
fail May. Only four strict-like selected rows are May-positive, all from the
old WPR106-199 post-190 composite pocket that already requires source-level
controls. The best May row is WPR106-133 cross-symbol relative strength, but
it is not strict-like because it has seven pre-May losing months and fails the
annual target.

WPR106-206 therefore rejects the broad noncanonical artifact scout set as
candidate-ready, portfolio-ready, paper/live-ready, or promotion-ready. The
useful next work is either a fresh calendar/session source reconstruction with
causal controls, or a cross-symbol lead-lag / anchored-VWAP transfer repair
focused on reducing pre-May losing months while keeping May held out.

Final close validation passed:

```powershell
python -m compileall -q data\research\wpr106_206_post205_broad_noncanonical_artifact_scout\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
