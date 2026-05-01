# Stage 4 Exit Report

Stage: Stage 4 - Point-in-time feature store and feature registry
Branch: `research/v3-experimental-engine`
Decision: complete
Date: 2026-05-01
Orchestrator: Codex

## Completed work packets

- WP4-01-feature-registry

## Validation commands run

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_feature_contracts.py tests/tradingbotsuite/test_feature_alignment.py tests/contracts/test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_feature_alignment.py tests/tradingbotsuite/test_hmm_knn.py tests/tradingbotsuite/test_archive_sources.py tests/tradingbotsuite/test_data_quality.py tests/tradingbotsuite/test_data_pipeline.py tests/tradingbotsuite/test_market_data_collection.py tests/tradingbotsuite/test_research.py -q
```

## Results

- `python -m compileall -q src/tradingbotsuite`: passed.
- Feature contract, alignment, and import-boundary tests passed, 15 tests.
- HMM/KNN research tests passed, 35 tests.
- Full contract suite passed, 19 tests.
- Feature, HMM/KNN, archive, data-quality, data-pipeline, market-data, and research regression tests passed, 97 tests.

## Artifacts produced

- `src/tradingbotsuite/features/__init__.py`
- `src/tradingbotsuite/features/alignment.py`
- `src/tradingbotsuite/features/registry.py`
- `src/tradingbotsuite/features/packs.py`
- `src/tradingbotsuite/features/preprocessing.py`
- `src/tradingbotsuite/research/feature_alignment.py`
- `configs/features/features_price_trend_vol.json`
- `configs/features/features_price_trend_vol_wt3d.json`
- `configs/features/features_perp_context_only.json`
- `configs/features/features_price_perp_micro_no_wt.json`
- `configs/features/features_full_context_wt3d.json`
- `configs/features/features_full_context_no_wt.json`
- `tests/contracts/test_feature_contracts.py`

## Known issues

- ISSUE-R1-001 remains open for later live-boundary enforcement.
- ISSUE-R1-002 remains open for Stage 10 live-mode research job rejection.
- Feature pack outputs are deterministic and contract-tested, but the existing HMM/KNN runner still consumes its config-declared columns directly. Full runner integration with preset manifests can be handled when Stage 5/experiment orchestration starts consuming feature-set metadata.

## Carry-forward debt

- Stage 5 should use feature manifests to validate backtest input frames and report missing feature context before running strategy evaluation.
- Cross-asset features are registered and explicit-missing when BTC/ETH columns are absent; ETH expansion remains a later-stage concern.

## Decision rationale

Stage 4 is complete because completed-bar alignment lives under the new feature package, feature manifests and hashes exist for all required presets, WT3D and no-WT sets are both registered, no-lookahead and missingness behavior are tested, and train-only preprocessing is covered by contract tests.
