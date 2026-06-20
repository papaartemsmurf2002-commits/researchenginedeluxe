# WPR106-166 WPR146 Source-Level Stability Ablation

Status: closed
Date: 2026-06-12
Stage: R106 strategy research

## Objective

Run a source-level, fail-closed stability and ablation audit around the
WPR106-146 cross-symbol relative-strength trade-veto clue. WPR106-165 preserved
this pocket as the strongest research-only follow-up, but the evidence remains
post-hoc because the pocket was already noticed through prior May 2026
benchmark summaries.

This packet must determine whether the WPR106-146 behavior is mostly raw-source
path exposure, a behavior-cluster artifact, a one-sided side effect, or a
repeatable pre-May stability improvement that deserves fresh non-May retesting.

All behavior-deduped row selection, raw-source comparisons, consensus filters,
rolling/pseudo-holdout diagnostics, side/opposite controls, and ranking use
2024-01-01 through 2026-04-30 only. May 2026 is used only after fixed rows,
thresholds, controls, and diagnostics are frozen.

## Allowed Paths

- `docs/work_packets/WPR106-166-wpr146-source-level-stability-ablation.md`
- `docs/stage_reports/STAGE_R106_WPR146_SOURCE_LEVEL_STABILITY_ABLATION_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_166_wpr146_source_level_stability_ablation/**`

## Inputs

- Read-only WPR106-146 artifacts under
  `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/**`.
- Read-only WPR106-146 runner helpers may be imported for source trade
  evaluation and WPR106-136 accounting helpers.
- WPR106-165 may be referenced for context, but this packet recomputes its own
  source-level controls from WPR106-146 frozen trades.

## Method

- Load WPR106-146 selected rows, behavior diagnostics, selected pre-May trades,
  selected May trades, raw-source/no-KNN controls, and side controls.
- Build a behavior-deduped selected row set using only pre-May behavior hashes,
  strict/profile status, pre-May selection score, stability metrics, and
  deterministic tie-breaks.
- Compare each behavior-deduped selected row against its raw-source daily-cap
  baseline by selected, common, excluded, and raw-only trades for pre-May and
  May, without using May for selection.
- Run rolling pre-May diagnostics over fixed selected rows, including yearly,
  half-year, and anchored future-window returns.
- Run opposite-side counterfactual diagnostics by flipping selected trade
  direction and preserving costs, to verify the edge is not direction-agnostic.
- Build pre-May-only consensus filters over behavior-deduped selected variants:
  count how many fixed variants accept each raw-source trade, select fixed vote
  thresholds from pre-May metrics, then benchmark those thresholds on May.
- Summarize raw-source path coupling, behavior clustering, side sensitivity,
  stability, active trade rates, costs, and May benchmark behavior.
- Keep outputs research-only, observe-only, and `promotion_ready: false`.

## Validation

- `python -m compileall -q data/research/wpr106_166_wpr146_source_level_stability_ablation/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

## Exit Criteria

- Write behavior-deduped rows, source-path ablations, rolling stability
  diagnostics, opposite-side controls, consensus-filter metrics, May benchmark
  diagnostics, summary, and stage report.
- Update the stage ledger with the packet decision.
- Do not write a candidate pack or make paper/live/promotion claims.

## Result

WPR106-166 loaded WPR106-146 frozen selected rows, behavior diagnostics,
selected/control trades, raw-source controls, and side controls. It selected 17
behavior-deduped representatives from pre-May behavior hashes only, computed
source-path ablations, rolling pre-May stability, opposite-side controls, and
pre-May-selected behavior-consensus filters, then benchmarked fixed rows and
thresholds on May 2026.

The 17 behavior representatives were all May-positive, with best +0.067949,
worst +0.015398, median +0.030569, and mean +0.037985. Opposite-side
counterfactuals were uniformly negative both pre-May and May, and standalone
long/short side controls failed pre-May profile checks. Raw no-KNN cap 3/5 was
already May-positive at +0.065272 and had +1.209539 pre-May net, but with seven
pre-May losing months and annual losses 4/3/0.

The clearest new descriptor is the pre-May-selected behavior-consensus
threshold 5 filter: 254 pre-May trades, 26 active months, two losing months,
annual losses 1/1/0, +1.155278 pre-May net, -0.141007 max drawdown,
best-month share 0.146280, full cost-stress survival, and +0.065272 May with
17 trades. This reaches the requested month-to-month stability profile on
pre-May evidence, but remains source-path-coupled because the May return
matches the raw cap 3/5 source path.

The packet rejects WPR106-166 as candidate-ready, portfolio-ready, or
promotion-ready evidence. It preserves WPR106-146 threshold-5 consensus as the
best research-only descriptor for a fresh non-May retest, preferably through a
direct strategy rebuild and later non-May holdout data. The run did not write a
candidate pack, paper/live artifact, live config, order path, sizing change,
CUDA speedup claim, or promotion claim. Focused script compile, package
compile, and contracts passed; contracts reported 460 passed.
