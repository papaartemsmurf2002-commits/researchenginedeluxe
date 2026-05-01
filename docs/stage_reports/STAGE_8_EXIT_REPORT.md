# Stage 8 Exit Report

Stage: Stage 8 - Experiment runner, optimizer, and reproducible tweaking protocol
Branch: `research/v3-experimental-engine`
Decision: complete
Date: 2026-05-02
Orchestrator: Codex

## Completed work packets

- WP8-01-generic-experiment-runner

## Validation commands run

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main run-hmm-knn-experiments --help
$env:PYTHONPATH='src'; python -m tradingbotsuite.main run-research-experiment --help
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_experiment_runner.py -q
```

## Results

- `run-hmm-knn-experiments --help`: passed.
- `run-research-experiment --help`: passed.
- Research suite passed, 19 tests.
- Experiment runner suite passed, 6 tests.

## Exit Gate

| Requirement | Evidence | Passed |
| --- | --- | --- |
| Experiments reproducible from manifests | `experiment_manifest.json` and copied specs in `run_research_experiment` outputs | yes |
| Cache identity deterministic | `deterministic_experiment_cache_key` tests | yes |
| Baseline strategy and HMM/KNN through same runner | Generic experiment summary includes `baseline_no_trade`, `trend_following_v1`, and `hmm_knn_diagnostic_v1` | yes |
| Split, side, regime, and cost stress summaries | `metrics_by_split.parquet`, `metrics_by_side.parquet`, `metrics_by_regime.parquet`, `metrics_by_cost_stress.parquet` | yes |
| Overfit/tuned results rejected explicitly | `orchestrator_decision.failure_reasons` and summary `failure_reasons` | yes |

## Carry-Forward

- Stage 9 can display the generic experiment outputs directly because every metric table links back to `experiment_manifest.json`.
