# WPR106-210 Directional KNN Stability Reselection

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Objective

Continue the 2024-forward broad strategy search by revisiting the discarded
WPR106-190 directional KNN confidence-entry universe. WPR106-190 had many
annual-target pre-May rows and unusually positive active May diagnostics, but
the original selected set was mostly unstable or inactive in May.

This packet asks whether the full WPR106-190 row universe can be repaired by
pre-May-only monthly stability, recent-coverage, active-rate, and behavior
de-duplication controls before May 2026 is replayed.

## Data And Selection Policy

- Use WPR106-190 directional KNN confidence-entry rows and source helpers.
- Optimize, filter, rank, and select only on 2024-01-01 through 2026-04-30.
- Keep May 2026 fully out of row scoring, stability controls, behavior
  de-duplication, and selected-row inclusion.
- Replay May 2026 only after fixed rows are selected from pre-May evidence.
- Permit active rates up to 1-5 trades per active day when overlap blocking,
  daily caps, costs, drawdown, and monthly stability are measured.
- All outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-210-directional-knn-stability-reselection.md`
- `docs/stage_reports/STAGE_R106_DIRECTIONAL_KNN_STABILITY_RESELECTION_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered
- `data/research/wpr106_210_directional_knn_stability_reselection/**`

No shared source package, checked strategy config, fixture catalog, live,
runtime, order-placement, sizing, candidate-pack, paper, or promotion path is
in scope unless this packet is amended before the edit.

## Planned Work

1. Create a packet-local artifact runner that imports the WPR106-190 runner
   and reloads its full pre-May ranking/monthly evidence.
2. Add stronger pre-May stability diagnostics: active recent months, latest
   Jan-April 2026 return/trade coverage, drop-best-month robustness,
   rolling-quarter and rolling-six-month floors, and consecutive losing-month
   clusters.
3. Preselect rows from the full WPR106-190 ranking using annual-target and
   loose/stability tiers rather than the original WPR106-190 selected set.
4. Replay pre-May accepted trades for preselected rows and behavior-deduplicate
   by accepted trade path.
5. Replay May 2026 only for the frozen selected rows.
6. Decide whether any directional KNN confidence-entry row remains a
   research-only promising lead after these controls.

## Research Boundary

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim. CUDA is not planned. Compute acceleration is limited
to reusing WPR106-190 cached source logic plus vectorized pandas/numpy
artifact processing.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_210_directional_knn_stability_reselection\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Closeout Evidence

The completed runner loaded the full WPR106-190 directional KNN pre-May row
universe and monthly evidence, added stronger pre-May stability diagnostics,
preselected 240 rows, replayed accepted pre-May trades, and behavior-deduped
the set to 100 fixed selected rows before May was replayed.

Source WPR106-190 evidence contained 23,328 rows, 6,014 positive pre-May rows,
2,396 positive annual-target rows, 11 loose rows, and zero strict rows. The
annual-target rows were sparse: zero positive annual-target rows had at least
20 active months and 60 trades.

The behavior-deduped WPR106-210 selected set contains 96
`annual_sparse_control` rows and four `loose_recent_stability` rows. Selected
pre-May replay had 100 positive rows, median return +0.082670, active mean
+0.087520, best +0.347297, and worst +0.011914.

May 2026 rejected the fixed set: 100 benchmark rows produced only one active
row, with 0 positive, 1 negative, and 99 flat rows. Median May return was
0.000000, active mean May return was -0.000946, and the sole active row lost
-0.000946 on one trade.

WPR106-210 therefore rejects directional KNN stability reselection as
candidate-ready, portfolio-ready, paper/live-ready, or promotion-ready. The
useful evidence is that WPR106-190's annual-target count was driven by sparse
rows, while active directional-KNN ETHUSDT short rows remain May-inactive under
stricter pre-May stability controls.

Final validation passed:

```powershell
python -m compileall -q data\research\wpr106_210_directional_knn_stability_reselection\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed. No CUDA path was used and no speedup was
claimed.
