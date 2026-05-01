# Stage 7 Exit Report

Stage: Stage 7 - HMM/KNN refactor and feature-agnostic analog engine
Branch: `research/v3-experimental-engine`
Decision: complete
Date: 2026-05-01
Orchestrator: Codex

## Completed work packets

- WP7-01-hmm-knn-refactor

## Validation commands run

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m tradingbotsuite.main research-hmm-knn --config configs/v2_btc_hmm_multi_knn_research.json --help
$env:PYTHONPATH='src'; python -m tradingbotsuite.main monitor-hmm-knn --help
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_strategy_contracts.py tests/contracts/test_import_boundaries.py tests/integration/test_backtest_engine_fixture.py -q
```

## Results

- `python -m compileall -q src/tradingbotsuite`: passed.
- `research-hmm-knn --help`: passed.
- `monitor-hmm-knn --help`: passed.
- HMM/KNN research regression suite passed, 37 tests.
- Strategy contract, import-boundary, and backtest engine fixture checks passed, 15 tests.

## Artifacts produced

- `src/tradingbotsuite/strategies/hmm_knn/__init__.py`
- `src/tradingbotsuite/strategies/hmm_knn/config.py`
- `src/tradingbotsuite/strategies/hmm_knn/regimes.py`
- `src/tradingbotsuite/strategies/hmm_knn/distances.py`
- `src/tradingbotsuite/strategies/hmm_knn/neighbors.py`
- `src/tradingbotsuite/strategies/hmm_knn/meta.py`
- `src/tradingbotsuite/strategies/hmm_knn/artifacts.py`
- `src/tradingbotsuite/strategies/hmm_knn/diagnostics.py`
- `src/tradingbotsuite/strategies/hmm_knn/plugin.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `tests/tradingbotsuite/test_hmm_knn.py`

## Exit Gate

| Requirement | Evidence | Passed |
| --- | --- | --- |
| HMM/KNN can run with WT3D and without WT3D | Existing WT3D artifact test plus `full_context_no_wt3d` Euclidean run test | yes |
| HMM/KNN can run with at least two distance functions | Lorentzian, Euclidean robust-z, and cosine resolvers; Euclidean run test | yes |
| Research-only artifact boundaries retained | Manifest and benchmark assertions keep `research_only`, `observe_only`, `promotion_ready: false` | yes |
| KNN diagnostics report neighbor quality and no-trade reasons | `artifact_diagnostics.neighbor_distance_quality_distribution` and `no_trade_reason_breakdown` | yes |
| Benchmarked against Stage 6 baselines | `stage6_baseline_benchmark` runs `trend_following_v1` and `baseline_no_trade` | yes |

## Known Issues

- ISSUE-R1-001 remains open for later live-boundary enforcement.
- ISSUE-R1-002 remains open for Stage 10 live-mode research job rejection.
- Mahalanobis distance is intentionally deferred until train-only covariance behavior is specified and tested.

## Carry-Forward

- Stage 8 should generalize experiment running beyond HMM/KNN, add optimizer constraints, and record anti-overfit evidence.
- Stage 8 should use the Stage 7 `stage6_baseline_benchmark` outputs as comparison inputs for experiment summaries.

## Decision Rationale

Stage 7 is complete because the HMM/KNN strategy surface is now package-based, distance and feature-pack selection are configurable, deterministic regime fallback is available, diagnostics cover the requested no-trade and neighbor-quality dimensions, artifacts remain research-only, and Stage 6 baselines are benchmarked alongside HMM/KNN outputs.
