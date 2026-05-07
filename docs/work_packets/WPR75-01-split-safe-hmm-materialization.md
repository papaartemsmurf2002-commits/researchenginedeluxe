# WPR75-01 Split-Safe HMM Materialization

Stage: R75 split-safe HMM materialization foundation
Owner: Codex Research Agent
Status: closed
Created: 2026-05-07

## Goal

Add a reusable discovery-side regime materialization foundation that fits only
on training rows for each walk-forward split and writes HMM-compatible posterior
columns for validation rows. This packet creates the split-safety artifact
contract needed before regime-local KNN studies.

## Allowed Paths

```text
src/tradingbotsuite/research_discovery/**
configs/discovery/**
tests/research_discovery/**
docs/work_packets/WPR75-01-split-safe-hmm-materialization.md
docs/stage_reports/STAGE_R75_SPLIT_SAFE_HMM_MATERIALIZATION_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Fit regime models only on training rows for each split.
- Emit `hmm_fit_end_row < source_row_index` for every actionable posterior row.
- Do not use full-dataset scalers, full-dataset posteriors, or validation rows
  in fitted transforms.
- Do not implement KNN search, strategy candidate wiring, optimizer behavior,
  operator UI behavior, candidate-pack bridge behavior, live execution,
  promotion behavior, sizing, or order placement.
- Preserve research-only, observe-only, promotion-ready false boundaries.

## Required Output

- Discovery HMM materialization dataclasses and functions.
- HMM materialization spec config under `configs/discovery/`.
- Focused tests for train-only fitting, split safety, required output columns,
  deterministic fallback behavior, insufficient-training fail-closed behavior,
  and manifest boundary flags.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
```

Run full contracts before closing if shared contracts change.

## Close Evidence

- Added `tradingbotsuite.research_discovery.hmm_materialization` with
  train-only per-split Gaussian-mixture regime materialization.
- Emitted the required HMM posterior/router columns including `hmm_model_id`,
  `hmm_feature_pack_id`, and `hmm_split_id`.
- Added artifact writing for `hmm_materialization_manifest.json`,
  `regime_posteriors.parquet`, and `hmm_split_summary.parquet`.
- Added `configs/discovery/hmm_materialization_v4.json`.
- Added focused tests for split-safety, finite posterior probabilities,
  train-only future perturbation behavior, insufficient-training fail-closed
  behavior, missing-column rejection, artifact boundary flags, and config load.
- Validation passed on 2026-05-07 with compile and focused discovery tests.
