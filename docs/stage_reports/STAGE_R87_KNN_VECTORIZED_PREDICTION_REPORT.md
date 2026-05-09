# Stage R87 KNN Vectorized Prediction Report

Date: 2026-05-09
Packet: `docs/work_packets/WPR87-01-knn-vectorized-prediction.md`

## Scope

WPR87 optimized the discovery regime-local KNN materializer without changing
research semantics, artifact contracts, live behavior, or promotion readiness.

## Changes

- `materialize_regime_local_knn_predictions` now transforms validation rows
  once per split and predicts from precomputed numpy vectors.
- Row prediction logic is centralized in `_predict_precomputed_row`, while
  `_predict_row` remains available as a compatibility helper.
- KNN manifests record `prediction_engine:
  split_local_vectorized_validation_v1`.
- Focused tests compare vectorized split prediction with the original row
  helper on identical training, validation, labels, regimes, and diagnostics.

## Boundary

- Research-only metadata remains unchanged: `research_only: true`,
  `observe_only: true`, and `promotion_ready: false`.
- The KNN study still enforces
  `neighbor_min_source_index <= neighbor_max_source_index <= hmm_fit_end_row <
  source_row_index`.
- The label-safety rule remains
  `training_label_source_row_index + label_horizon_bars <
  validation_source_row_index`.
- No live adapter imports, live execution, order placement, candidate-pack gate
  weakening, or promotion behavior changes were added.

## Validation

- `python -m compileall -q src\tradingbotsuite\research_discovery`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_knn_study.py -q`
  - `10 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
  - `75 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_benchmark.py -q`
  - `7 passed`
- `$env:PYTHONPATH='src'; python -m tradingbotsuite.main benchmark-discovery-run --tier quick --repeat 1 --output-dir <temp>`
  - `benchmark_gate_passed: true`
  - `evidence_complete: true`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `372 passed`

## Exit Decision

Stage R87 is complete. The discovery KNN study now avoids per-validation-row
pandas scaler work while preserving existing outputs and split-safety evidence.
