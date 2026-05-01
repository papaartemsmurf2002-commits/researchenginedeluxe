# Work Packet WP7-01 - HMM/KNN Refactor

Stage: Stage 7 - HMM/KNN refactor and feature-agnostic analog engine
Owner: Orchestrator Agent
Status: closed
Date: 2026-05-01

## Objective

Refactor the research HMM/KNN path into a configurable package with pluggable regimes, distances, feature packs, diagnostics, and Stage 6 baseline comparison while preserving research-only boundaries.

## Scope

- Split the Stage 6 HMM/KNN strategy file into `src/tradingbotsuite/strategies/hmm_knn/**`.
- Add feature-pack presets for WT3D, no-WT3D, price/trend/vol, perp context, and microstructure context.
- Add pluggable distance functions for Lorentzian/log-Lorentzian, Euclidean robust-z, and cosine.
- Add deterministic rule-based regime baseline alongside HMM/GMM research fitting.
- Add artifact diagnostics for neighbor quality, no-trade reasons, regime acceptance, missingness, KNN/meta comparison, and WT3D ablation status.
- Benchmark HMM/KNN research artifacts against Stage 6 baseline strategies.

## Exit Evidence

- `src/tradingbotsuite/strategies/hmm_knn/config.py`
- `src/tradingbotsuite/strategies/hmm_knn/regimes.py`
- `src/tradingbotsuite/strategies/hmm_knn/distances.py`
- `src/tradingbotsuite/strategies/hmm_knn/neighbors.py`
- `src/tradingbotsuite/strategies/hmm_knn/meta.py`
- `src/tradingbotsuite/strategies/hmm_knn/artifacts.py`
- `src/tradingbotsuite/strategies/hmm_knn/diagnostics.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `docs/stage_reports/STAGE_7_EXIT_REPORT.md`

## Validation

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m tradingbotsuite.main research-hmm-knn --config configs/v2_btc_hmm_multi_knn_research.json --help
$env:PYTHONPATH='src'; python -m tradingbotsuite.main monitor-hmm-knn --help
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_strategy_contracts.py tests/contracts/test_import_boundaries.py tests/integration/test_backtest_engine_fixture.py -q
```

## Notes

- Mahalanobis and learned embeddings remain later-stage work; Stage 7 requires at least two operational distances and includes three.
- Outputs remain `research_only`, `observe_only`, and `promotion_ready: false`.
