# Stage 12.1 Exit Report

Stage: Stage 12 - Later-stage research expansion and institutional tuning
Substage: 12.1 Feature ablation and replacement
Branch: `research/v3-experimental-engine`
Decision: complete
Date: 2026-05-03
Orchestrator: Codex

## Completed work packets

- WP12-01-feature-ablation-and-replacement

## Validation commands run

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

## Results

- `tests/tradingbotsuite/test_feature_ablation.py`: 3 passed.
- `tests/contracts/test_feature_contracts.py`: 7 passed.
- `tests/live/test_preflight.py`: 5 passed.
- `plan-feature-ablation --help`: passed.
- `plan-feature-ablation` temp run: passed and wrote 8 per-hypothesis experiment specs.
- `tests/contracts`: 31 passed.
- `tests/live`: 19 passed.
- Feature ablation plus experiment runner regression: 9 passed.
- `compileall`: passed with no syntax errors.

## Artifacts produced

- `src/tradingbotsuite/research/feature_ablation.py`
- `configs/features/features_microstructure_filter_only.json`
- `configs/features/features_cross_asset_context.json`
- `tests/tradingbotsuite/test_feature_ablation.py`
- `docs/work_packets/WP12-01-feature-ablation-and-replacement.md`

## Exit gate

| Requirement | Evidence | Passed |
| --- | --- | --- |
| Full Stage 12.1 track list is represented | `stage12_feature_ablation_tracks()` and tests | yes |
| Reproducible experiment manifests can be produced | `write_feature_ablation_plan()` and tests | yes |
| Rejected or pending hypotheses are documented | `rejected_hypotheses.md` output and tests | yes |
| Accepted hypotheses require OOS and stress gates | `_decide_hypothesis()` and tests | yes |
| No model is accepted from in-sample-only evidence | `test_stage12_feature_ablation_rejects_weak_evidence_and_accepts_only_oos_stress` | yes |
| Feature ablation CLI is rejected in live mode | `tests/live/test_preflight.py` | yes |

## Carry-forward

- Stage 12.2 Regime model comparison should add regime stability, transition frequency, no-trade rate, per-regime expectancy, and regime drift outputs.
- Stage 12 remains in progress until all research tracks 12.1 through 12.7 produce reproducible manifests and rejected-hypothesis records.
