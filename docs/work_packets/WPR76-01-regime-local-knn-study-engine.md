# WPR76-01 Regime-Local KNN Study Engine

Stage: R76 regime-local KNN study foundation
Owner: Codex Research Agent
Status: closed
Created: 2026-05-07

## Goal

Add a bounded discovery-side regime-local KNN study foundation that consumes
split-safe HMM materialized rows and emits KNN prediction columns for validation
rows. This packet creates the local analog prediction contract needed before
strategy integration.

## Allowed Paths

```text
src/tradingbotsuite/research_discovery/**
configs/discovery/**
tests/research_discovery/**
docs/work_packets/WPR76-01-regime-local-knn-study-engine.md
docs/stage_reports/STAGE_R76_REGIME_LOCAL_KNN_STUDY_ENGINE_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Use only train rows available before each validation row.
- Enforce `neighbor_min_source_index <= neighbor_max_source_index <=
  hmm_fit_end_row < source_row_index`.
- Keep KNN feature-column sets bounded and explicit.
- Do not add strategy candidate wiring, historical-cycle integration, optimizer
  behavior, operator UI behavior, candidate-pack bridge behavior, live
  execution, promotion behavior, sizing, or order placement.
- Preserve research-only, observe-only, promotion-ready false boundaries.

## Required Output

- Discovery KNN study dataclasses and functions.
- KNN study config under `configs/discovery/`.
- Focused tests for split safety, same-regime neighbor pools, train-only future
  perturbation behavior, blocked insufficient neighbors, prediction columns, and
  artifact boundary flags.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
```

Run full contracts before closing if shared contracts change.

## Close Evidence

- Added `tradingbotsuite.research_discovery.knn_study` with a deterministic
  CPU reference KNN study engine.
- Added same-regime local neighbor pools, train-only scaling, Euclidean,
  Manhattan, and cosine distances, prediction columns consumed by existing
  HMM/KNN strategy contracts, and neighbor diagnostics.
- Added artifact writing for `knn_study_manifest.json`,
  `knn_predictions.parquet`, and `neighbor_diagnostics.parquet`.
- Added `configs/discovery/knn_study_v4.json`.
- Added focused tests for split-safe neighbor bounds, same-regime diagnostics,
  train-only future perturbation behavior, insufficient-neighbor blockers,
  missing-column rejection, artifact boundary flags, and config load.
- Validation passed on 2026-05-07 with compile and focused discovery tests.
