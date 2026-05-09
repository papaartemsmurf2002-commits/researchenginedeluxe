# WPR89-01 KNN Deterministic Top-K

## Objective

Reduce regime-local KNN CPU cost by replacing full per-row candidate distance
sorts with deterministic top-k selection, preserving neighbor order, tie
behavior, diagnostics, and output contracts.

## Fit Check

This fits the current architecture because it stays inside the discovery KNN
study engine, adds no new dependency, keeps split/label safety unchanged, and
does not alter discovery trial generation, artifact schemas, candidate gates,
promotion readiness, or live behavior.

## Allowed paths

- `src/tradingbotsuite/research_discovery/knn_study.py`
- `tests/research_discovery/test_knn_study.py`
- `docs/work_packets/WPR89-01-knn-deterministic-topk.md`
- `docs/stage_reports/STAGE_R89_KNN_DETERMINISTIC_TOPK_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered

## Planned changes

- Add a helper that selects nearest-neighbor positions using `np.partition`
  instead of full `np.argsort` when the candidate pool is larger than `k`.
- Preserve old stable tie semantics by including all candidates tied at the
  kth distance, then stable-sorting that reduced set before truncation.
- Record the selection engine in the KNN manifest.
- Add focused regression coverage proving top-k output matches full stable sort,
  including a boundary-tie case.

## Exit criteria

- Focused KNN tests pass.
- Full discovery tests pass.
- Compile and contract baseline pass.
- Stage report records implementation and validation.
