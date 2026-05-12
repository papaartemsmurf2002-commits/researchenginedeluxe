# Stage R94 Regime Baseline And Naming Truthfulness Report

Date: 2026-05-12
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR94-01-regime-baseline-naming-truthfulness.md`

## Summary

WPR94-01 implemented explicit discovery regime modes and made the current
regime backend truthful in manifests and operator-facing discovery copy.

Implemented:

- Added the discovery `regime_mode` axis:
  - `none`
  - `gmm_gate_only`
  - `gmm_same_regime_neighbors`
  - `gmm_all_regime_neighbors_with_gate`
- Added mode-derived trial, KNN, ledger, and run-manifest fields:
  - `regime_detector_type`
  - `regime_mode`
  - `regime_gate_enabled`
  - `same_regime_neighbor_pool_enabled`
  - `true_hmm_backend_used`
- Added no-regime split-safe compatibility materialization so KNN trials can
  run without fitting GMM, without applying `regime_no_trade`, and without
  restricting neighbors to same-regime pools.
- Preserved existing HMM-compatible column names where downstream strategy and
  artifact contracts still require them, while labeling the backend as GMM in
  manifests.
- Updated standard/deep discovery configs to include no-regime and GMM modes.
- Updated focused Research UI/docs copy to describe current V4 discovery as
  GMM-regime/KNN with no-regime baselines rather than true HMM.

## Boundary Notes

- Research outputs remain `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.
- No live order placement, live config writes, runtime mode changes, candidate
  promotion, or sizing behavior was added.
- No true HMM backend was added.
- Candidate-pack bridge behavior remains observe-only and pack-writing remains
  disabled.

## Validation

Passed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_spec.py tests\research_discovery\test_hmm_materialization.py tests\research_discovery\test_knn_study.py tests\research_discovery\test_discovery_runner.py -q
# 44 passed

$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_candidate_pack_bridge.py -q
# 13 passed

$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
# 35 passed

python -m compileall -q src\tradingbotsuite

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 372 passed

$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
# 86 passed

git diff --check
# passed
```

## Next Packet

Continue the R94 roadmap with WPR94-02 independent event accounting and score
redesign. The current implementation still preserves the legacy density score;
overlapping bar-signal inflation is intentionally left for the next packet.
