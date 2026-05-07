# Stage R75 Split-Safe HMM Materialization Report

Date: 2026-05-07
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR75-01-split-safe-hmm-materialization.md`

## Scope

WPR75 adds a discovery-side split-safe HMM materialization foundation. It does
not add KNN search, strategy candidate wiring, optimizer behavior, operator UI
behavior, candidate-pack bridge behavior, promotion readiness, live execution,
sizing, or order placement.

## Changes

- Added `src/tradingbotsuite/research_discovery/hmm_materialization.py`.
- Added `configs/discovery/hmm_materialization_v4.json`.
- Added focused tests in `tests/research_discovery/test_hmm_materialization.py`.

The materializer:

- fits a Gaussian mixture regime model only on each split's training rows;
- uses train-only robust scaling;
- emits validation-row posterior columns compatible with existing HMM router
  strategies;
- records `hmm_fit_end_row < source_row_index` evidence for every materialized
  row;
- keeps insufficient training splits blocked and non-actionable;
- writes `hmm_materialization_manifest.json`, `regime_posteriors.parquet`, and
  `hmm_split_summary.parquet`.

## Evidence

Generated HMM materialization manifests record:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `order_placement_used: false`
- `runtime_mode_changed: false`
- `split_safety_rule: hmm_fit_end_row < source_row_index`
- `split_safety_passed: true`

Focused tests prove that perturbing future rows after an already-scored split
does not change that split's posteriors.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
```

Results:

- Compile passed.
- Discovery tests passed: 27 passed.

## Limitations

This packet materializes regimes only. Regime-local KNN studies, KNN prediction
materialization, strategy integration, operator controls, and candidate-pack
bridge behavior remain later packets.
