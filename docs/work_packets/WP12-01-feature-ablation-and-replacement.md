# Work Packet WP12-01 - Feature Ablation And Replacement

Stage: Stage 12 - Later-stage research expansion and institutional tuning
Substage: 12.1 Feature ablation and replacement
Owner: Orchestrator Agent
Status: closed
Date: 2026-05-03

## Objective

Create the reproducible Stage 12.1 planning layer for feature-pack ablation before deeper research tracks can claim model value.

## Scope

- Add first-class feature presets for `features_microstructure_filter_only` and `features_cross_asset_context`.
- Add `src/tradingbotsuite/research/feature_ablation.py` to enumerate every Stage 12.1 plan track.
- Write feature ablation manifests, per-hypothesis experiment specs, summary CSVs, and rejected/pending hypothesis notes.
- Add `plan-feature-ablation` CLI entrypoint with live-mode research-command guard.
- Add tests for required track coverage, deterministic outputs, weak-evidence rejection, and CLI execution.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_feature_ablation.py -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_feature_contracts.py -q
$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q
$env:PYTHONPATH='src'; python -m tradingbotsuite.main plan-feature-ablation --help
$env:PYTHONPATH='src'; python -m tradingbotsuite.main plan-feature-ablation --output-dir "$env:TEMP\stage12-feature-ablation-smoke" --dataset-manifest-hash sha256:validation
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m pytest tests/live -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_feature_ablation.py tests/tradingbotsuite/test_experiment_runner.py -q
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
```
