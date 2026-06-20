# WPR106-137 Diversity-Constrained KNN Veto Ensemble

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Test whether the WPR106-136 KNN trade-veto overlay is useful only as a
standalone row filter or whether diverse veto-filtered rows can combine into a
more month-stable portfolio. This packet explicitly addresses the WPR106-136
failure mode by requiring source, packet, and family diversity before any May
benchmark.

## Allowed Paths

- `docs/work_packets/WPR106-137-diversity-constrained-knn-veto-ensemble.md`
- `docs/stage_reports/STAGE_R106_DIVERSITY_CONSTRAINED_KNN_VETO_ENSEMBLE_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/**`

## Inputs

- `data/research/wpr106_136_cross_family_knn_trade_veto_search/pre_may/knn_trade_veto_ranking.parquet`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/pre_may/source_pool.parquet`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/pre_may/source_pool_trades_pre_and_may.parquet`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/scripts/run_wpr106_136_cross_family_knn_trade_veto_search.py`

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, live configuration write, or promotion claim.
- May 2026 must not influence overlay-universe choice, ensemble construction,
  diversity constraints, ranking, daily caps, or selection.
- May 2026 may be replayed only after fixed strict pre-May ensembles are
  selected, or fixed loose ensembles if strict is empty.
- Replayed overlay source rows must keep the WPR106-136 causal rule: pre-May
  trades use earlier completed source-trade outcomes, and May uses frozen
  pre-May history only.
- CUDA may be used only if a real path is executed and represented truthfully.
  The expected path is CPU/vectorized portfolio accounting with no speedup
  claim.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Load WPR106-136 pre-May ranking and choose fixed loose/strict KNN-veto
   overlays without May feedback.
2. De-duplicate to a bounded overlay universe with at most a few top overlays
   per source and explicit packet/family diversity.
3. Replay those overlays through the WPR106-136 causal scoring functions to
   materialize pre-May and, after selection, May trades.
4. Construct equal-sleeve ensembles requiring multiple source packets and
   families, enforcing same-symbol overlap and daily trade caps at the
   ensemble level.
5. Select strict ensembles first; select loose only if strict is empty. If
   neither exists, do not benchmark May.
6. Replay May 2026 only for the fixed selected ensembles and report it as a
   separate benchmark.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed:

- `python -m compileall -q data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

## Closeout

Closed as a rejected research lead. The run built a 120-row KNN-veto overlay
universe from WPR106-136 evidence, covering 103 unique source rows, five source
packets, and 16 families. It generated 6,511 diverse member sets and evaluated
13,022 ensemble rows under daily caps of 3 and 5 trades. Pre-May selection was
strong on the 2024-01-01 through 2026-04-30 optimization window: all 13,022
rows were positive, 3,545 met the annual-target screen, 12,557 met loose
criteria, and 3,531 met strict criteria.

The fixed top-100 strict selection was then benchmarked on May 2026 only. May
rejected the lead: 15 selected rows were positive, 85 were negative, none were
flat, the best May return was +0.019375, the worst was -0.045451, and the
median was -0.015958. The result indicates that source/family diversity and
active 1-5 trades/day accounting did not solve the WPR106-136 holdout failure.
No candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim exists.
