# Work Packet: WP4-01-feature-registry

Stage: Stage 4 - Point-in-time feature store and feature registry
Owner agent: Feature Agent
Reviewer agent: QA Agent
Branch: `research/v3-experimental-engine`
Allowed paths:

- `src/tradingbotsuite/features/**`
- `src/tradingbotsuite/research/feature_alignment.py`
- `configs/features/**`
- `tests/contracts/test_feature_contracts.py`
- `tests/contracts/test_import_boundaries.py`
- `tests/tradingbotsuite/test_feature_alignment.py`
- `docs/contracts/feature_contract.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WP4-01-feature-registry.md`
- `docs/stage_reports/STAGE_4_EXIT_REPORT.md`

Forbidden paths:

- live runtime execution behavior
- order placement adapters
- generated data, secrets, databases, logs, caches, and local artifacts

## Objective

Create a feature registry and point-in-time feature pack layer that supports WT3D, no-WT, and alternative feature sets without leaking future rows.

## Required source files read first

- `docs/contracts/feature_contract.md`
- `src/tradingbotsuite/research/feature_alignment.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `tests/tradingbotsuite/test_feature_alignment.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `configs/v2_btc_hmm_multi_knn_research.json`

## Implementation tasks

- Move completed-bar alignment into `src/tradingbotsuite/features/alignment.py`.
- Keep `src/tradingbotsuite/research/feature_alignment.py` as a compatibility shim.
- Add feature registry dataclasses and manifest validation.
- Add feature packs for price path, trend/chop, volatility, perp context, microstructure context, WT3D, cross-asset context, and calendar context.
- Add required feature preset manifests under `configs/features/`.
- Add train-only scaler/imputer utilities.
- Add contract tests for manifests, no-lookahead behavior, missingness, and train-only preprocessing.

## Tests and validation commands

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_feature_contracts.py tests/tradingbotsuite/test_feature_alignment.py tests/contracts/test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
```

## Acceptance evidence

- `src/tradingbotsuite/features/alignment.py`
- `src/tradingbotsuite/features/registry.py`
- `src/tradingbotsuite/features/packs.py`
- `src/tradingbotsuite/features/preprocessing.py`
- `configs/features/*.json`
- `tests/contracts/test_feature_contracts.py`
- `docs/stage_reports/STAGE_4_EXIT_REPORT.md`

## Handoff notes

Stage 5 can consume feature manifests and feature frames for backtest input validation. The HMM/KNN path remains research-only and continues to pass its existing test suite.
