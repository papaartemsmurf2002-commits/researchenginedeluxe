# Stage R76 Regime-Local KNN Study Engine Report

Date: 2026-05-07
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR76-01-regime-local-knn-study-engine.md`

## Scope

WPR76 adds a discovery-side regime-local KNN study foundation. It does not add
historical-cycle candidate wiring, optimizer behavior, operator UI behavior,
candidate-pack bridge behavior, promotion readiness, live execution, sizing, or
order placement.

## Changes

- Added `src/tradingbotsuite/research_discovery/knn_study.py`.
- Added `configs/discovery/knn_study_v4.json`.
- Added focused tests in `tests/research_discovery/test_knn_study.py`.

The KNN study engine:

- consumes split-safe HMM materialized rows;
- uses train-only scaling;
- uses same-regime local neighbor pools by default;
- supports deterministic CPU Euclidean, Manhattan, and cosine distances;
- emits the KNN prediction columns consumed by existing HMM/KNN strategy
  contracts;
- records neighbor diagnostics;
- enforces `neighbor_min_source_index <= neighbor_max_source_index <=
  hmm_fit_end_row < source_row_index`;
- writes `knn_study_manifest.json`, `knn_predictions.parquet`, and
  `neighbor_diagnostics.parquet`.

## Evidence

Generated KNN study manifests record:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `order_placement_used: false`
- `runtime_mode_changed: false`
- split-safety rule and pass/fail status

Focused tests prove that perturbing rows after an already-scored split does not
change that split's KNN predictions.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
```

Results:

- Compile passed.
- Discovery tests passed: 34 passed.

## Limitations

This packet is a correctness-oriented reference study engine. It does not yet
wire KNN predictions into historical-cycle candidate generation, run optimizer
searches, expose operator controls, or bridge accepted discovery winners into
candidate-pack validation.
