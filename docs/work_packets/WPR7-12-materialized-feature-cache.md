# WPR7-12 Materialized Feature Cache

Status: closed
Owner: Codex Research Agent
Stage: Stage R7/R12 materialized feature computation and cache benchmark
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Replace historical-cycle pass-through feature declarations with materialized registered feature frames and deterministic feature-cache artifacts. The benchmark must measure real feature-build cache reuse honestly, while candidate acceptance remains blocked.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR7-12-materialized-feature-cache.md`
- `docs/stage_reports/STAGE_R7_R12_MATERIALIZED_FEATURE_CACHE_REPORT.md`
- `src/tradingbotsuite/features/builders.py`
- `src/tradingbotsuite/features/cache.py`
- `src/tradingbotsuite/features/__init__.py`
- `src/tradingbotsuite/research_cycle/benchmark.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `tests/features/test_feature_builders.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `tests/historical/test_full_cycle_local_fixture_pack.py`
- `tests/historical/test_research_cycle_benchmark.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/live/test_preflight.py`

## Non-goals

- No backtest artifact reuse/cache shortcut.
- No live, paper, shadow, testnet, or canary execution.
- No promotion-ready candidate acceptance.
- No optimizer geometry refactor.
- No new provider ingestion or network-dependent fixture generation.

## Implementation plan

1. Add materialized feature-frame helper that builds registered feature sets, drops stale source feature columns, merges computed features back onto canonical OHLCV/symbol rows, and preserves non-feature context columns.
2. Extend feature cache manifests with artifact hashes, feature/availability columns, build parameters, and read/validate helpers.
3. Update historical research cycle to build or load feature frames once per feature set, write feature artifacts, and feed the candidate's materialized feature frame into aggregate, split, and cost-stress backtests.
4. Update benchmark feature timing to run a cold and warm feature-cache pass and report feature-cache speedup without claiming backtest cache speedup.
5. Add tests that stale fixture features are replaced, materialized feature artifacts are written, benchmark cache evidence is measured, and live preflight still rejects research commands.

## Exit criteria

- Feature build manifest uses materialized registered feature sets, not pass-through status.
- Backtest manifests reference materialized feature manifest hashes for candidate feature sets.
- Feature cache manifests include content hashes and validate cache hits before reuse.
- Benchmark reports measured `feature_build_cache` cold/warm evidence.
- Focused tests, contracts, live preflight, compileall, and `git diff --check` pass.

## Risk controls

- Feed backtests materialized frames merged with OHLCV, not bare feature matrices.
- Slice already-built feature frames for validation splits; do not recompute features on validation-only slices.
- Keep all artifacts `research_only: true`, `observe_only: true`, and `promotion_ready: false`.
- If a cache manifest/path/hash mismatch is found, rebuild rather than reuse.

## Exit evidence

- Materialized feature frames are built from registered feature sets, merged onto canonical OHLCV/context rows, and all stale registered source feature columns are dropped before merge.
- Feature cache artifacts now write logical frame hashes, parquet artifact hashes, cache identity, feature/availability columns, nested feature manifests, and validated cache-hit reads.
- Historical-cycle aggregate, split, and cost-stress backtests consume the candidate feature set's materialized frame. Aggregate backtest manifests now carry the candidate feature-set manifest hash and dataset hash matching the feature-build record.
- Benchmark reports measured `feature_build_cache` cold/warm reuse only when the cold run fully builds, the warm run fully reuses, and feature output hashes match. It does not claim backtest cache reuse.
- Review agents rechecked the stale-feature, cache-validation, provenance, frame-hash, and benchmark-measurement fixes and reported no blocking findings.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/features/test_feature_builders.py tests/historical/test_full_cycle_synthetic.py tests/historical/test_full_cycle_local_fixture_pack.py tests/historical/test_research_cycle_benchmark.py -q` passed: 14 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed: 44 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q` passed: 24 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/features tests/historical -q` passed: 14 passed.
- `git diff --check` passed with only existing LF-to-CRLF warnings.
