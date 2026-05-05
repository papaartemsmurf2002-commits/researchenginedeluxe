# WPR9-10-12 KNN Diagnostics, Fixture Packs, and Benchmarks

Status: closed
Owner: Codex Research Agent
Stage: Stage R9/R10/R12 research completion foundations
Opened: 2026-05-04

## Objective

Advance the research branch without crossing live or promotion boundaries by implementing a bounded completion slice:

- R9: HMM/KNN diagnostic contract upgrades for distance metadata, neighbor-pool selection, regime matching, and feature-set identity.
- R10: validated offline historical fixture-pack manifests that the historical research cycle can load deterministically.
- R12: a small research-cycle benchmark gate with timing, throughput, memory, artifact-overhead, determinism, and explicit cache-status evidence.

All outputs remain research-only, observe-only, and not promotion-ready.

## Allowed paths

- `configs/v2_btc_hmm_multi_knn_research.json`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR9-10-12-knn-fixtures-benchmarks.md`
- `docs/stage_reports/STAGE_R9_R10_R12_RESEARCH_COMPLETION_REPORT.md`
- `src/tradingbotsuite/data/__init__.py`
- `src/tradingbotsuite/data/historical_fixture_pack.py`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/command_registry.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `src/tradingbotsuite/research/hmm_knn_experiments.py`
- `src/tradingbotsuite/research_cycle/__init__.py`
- `src/tradingbotsuite/research_cycle/benchmark.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/strategies/hmm_knn/diagnostics.py`
- `src/tradingbotsuite/strategies/hmm_knn/distances.py`
- `src/tradingbotsuite/strategies/hmm_knn/neighbors.py`
- `tests/contracts/test_data_contracts.py`
- `tests/contracts/test_historical_fixture_pack_contract.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/test_full_cycle_local_fixture_pack.py`
- `tests/historical/test_research_cycle_benchmark.py`
- `tests/live/test_preflight.py`
- `tests/tradingbotsuite/test_hmm_knn.py`

## Non-goals

- No live, paper, shadow, testnet, or canary execution.
- No live order adapter imports from research modules.
- No promotion-ready candidate acceptance.
- No network-dependent historical evidence generation.
- No broad backtest-engine rewrite.

## Implementation plan

1. Add explicit KNN distance metadata and regime-match diagnostics while preserving existing boolean config compatibility.
2. Add a reusable neighbor-pool selector that records before/after counts, selected counts, fallback state, skip reason, and resolved regime mode.
3. Add feature-set variant identity to HMM/KNN manifests and diagnostics without changing feature computation semantics.
4. Add `historical-fixture-pack-manifest-v1` validation and integrate it into historical-cycle dataset loading before legacy loose manifest handling.
5. Add a research-cycle benchmark report writer and CLI command using deterministic small/medium tiers.
6. Register all new research commands for live preflight rejection.
7. Add focused tests and run the branch validation baseline.

## Exit criteria

- HMM/KNN tests prove distance registry metadata, explicit regime-match modes, compatible/fallback behavior, and feature identity in artifacts.
- Fixture-pack contract tests reject unsafe/missing/hash-mismatched packs and full-cycle local pack tests do not fall back to synthetic data.
- Benchmark tests prove the report is research-only and includes positive throughput metrics, memory peak, artifact overhead, deterministic repeat hash, and honest cache-status evidence.
- `python -m compileall -q src/tradingbotsuite` passes.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passes.
- Focused historical, HMM/KNN, benchmark, and live-preflight tests pass.

## Exit evidence

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q` passed: 39 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_historical_fixture_pack_contract.py tests/historical/test_full_cycle_local_fixture_pack.py tests/historical/test_research_cycle_benchmark.py -q` passed: 8 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed: 44 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q` passed: 24 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/historical -q` passed: 8 passed.
- `git diff --check` passed with only existing LF-to-CRLF warnings.

## Completion notes

- Review-discovered P1/P2/P3 issues were fixed before closure:
  - Required fixture families now require hash, row count, and declared schema evidence.
  - Historical-cycle datasets are sorted by available bar time before aggregate and split evaluation.
  - Benchmark repeat directories are cleaned before each run so stale artifacts cannot inflate overhead.
  - Benchmark determinism coverage uses two repeats.
  - Explicit KNN regime modes no longer report contradictory `same_regime_only` diagnostics.
  - Compatible-mode diagnostics count query rows rather than neighbor rows.
  - Normalized Lorentzian aliases use the backend-aware Lorentzian path.

## Risk controls

- Preserve old HMM/KNN `same_regime_only` and `allow_cross_regime_fallback` config behavior.
- Keep fixture-pack raw family files separate from the wide cycle dataset expected by the research cycle.
- Report benchmark cache speedup as not measured until a persistent research-cycle execution cache exists.
- Keep all artifacts `research_only: true`, `observe_only: true`, and `promotion_ready: false`.
