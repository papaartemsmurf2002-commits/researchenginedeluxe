# WPR87-01 KNN Vectorized Prediction

## Objective

Improve regime-local KNN study runtime by replacing per-row pandas prediction
work with split-local numpy/batched prediction work, while preserving exact
research-only outputs and split-safety rules.

## Fit Check

This fits the current repository structure because it stays inside
`tradingbotsuite.research_discovery`, keeps the public KNN artifact contract,
does not introduce GPU or process-pool dependencies, and keeps train-only
scalers and label-horizon safety intact.

## Allowed paths

- `src/tradingbotsuite/research_discovery/knn_study.py`
- `tests/research_discovery/test_knn_study.py`
- `docs/work_packets/WPR87-01-knn-vectorized-prediction.md`
- `docs/stage_reports/STAGE_R87_KNN_VECTORIZED_PREDICTION_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered

## Planned changes

- Add a split-local vectorized prediction path that transforms validation rows
  once per split.
- Keep row-level diagnostics and output columns identical.
- Preserve same-regime filtering, source-row safety, distance metrics, thresholds,
  and deterministic tie handling.
- Add equivalence coverage against the prior row-prediction helper.

## Exit criteria

- KNN study tests pass.
- Full discovery test suite passes.
- Compile and contract baseline pass.
- Stage report records the implementation and validation.
