# Work Packet WP8-01 - Generic Experiment Runner

Stage: Stage 8 - Experiment runner, optimizer, and reproducible tweaking protocol
Owner: Orchestrator Agent
Status: closed
Date: 2026-05-02

## Objective

Generalize the research experiment runner so HMM/KNN and baseline strategies share a deterministic experiment, search, validation, cache, and reporting contract.

## Scope

- Add `ExperimentSpec`, `DatasetSpec`, `FeatureSpec`, `StrategySpec`, `BacktestSpec`, `ValidationSpec`, `SearchSpec`, and `ReportSpec`.
- Add deterministic cache identity using dataset, feature, strategy, engine, and validation hashes.
- Add deterministic grid, random, Latin-hypercube, and Sobol-style candidate expansion.
- Emit generic experiment artifacts alongside the existing run bundle:
  - `experiment_manifest.json`
  - `experiment_summary.csv`
  - `metrics_by_split.parquet`
  - `metrics_by_regime.parquet`
  - `metrics_by_side.parquet`
  - `metrics_by_cost_stress.parquet`
- Record overfit and stage-gate rejection reasons.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main run-hmm-knn-experiments --help
$env:PYTHONPATH='src'; python -m tradingbotsuite.main run-research-experiment --help
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_experiment_runner.py -q
```
