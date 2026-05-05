# Stage R7/R12 Materialized Feature Cache Report

Status: closed - materialized feature computation and cache benchmark implemented
Owner: Codex Research Agent
Date: 2026-05-04

## Scope

This wave completed the bounded R7/R12 materialized feature-cache foundation:

- Registered feature sets are materialized before historical-cycle backtests, merged onto canonical OHLCV/context rows, and stripped of stale registered source feature columns.
- Feature cache artifacts now include deterministic identity, logical frame hashes, parquet artifact hashes, feature/availability columns, nested feature manifests, availability reports, and validated cache-hit loading.
- Aggregate, walk-forward split, and cost-stress backtests consume the candidate feature set's materialized frame.
- Backtest manifests now use the candidate feature-set manifest hash, and aggregate dataset hashes match the feature-build record for the consumed frame.
- Historical-cycle benchmarks now run cold and warm feature-cache passes and report measured `feature_build_cache` reuse only when reuse is complete and output hashes match.

## Research Boundary

All new artifacts remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

No paper, shadow, testnet, live, canary, order-placement, live-mode mutation, or promotion-ready candidate path was added.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/features/test_feature_builders.py tests/historical/test_full_cycle_synthetic.py tests/historical/test_full_cycle_local_fixture_pack.py tests/historical/test_research_cycle_benchmark.py -q` passed: 14 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed: 44 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q` passed: 24 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/features tests/historical -q` passed: 14 passed.
- `git diff --check` passed with only LF-to-CRLF warnings.

## Review Resolution

Reviewers identified two P1 and two P2 risks during the packet. All were fixed before closure:

- Materialization now drops all registered feature and availability columns from the source before merging selected computed features.
- Cache-hit validation now checks requested identity fields, manifest identity, nested feature manifest, feature/availability columns, artifact path, parquet artifact hash, logical frame hash, row count, and required columns.
- Backtest provenance now uses the candidate feature set's manifest hash instead of the cycle-wide feature-build hash.
- Feature-build logical frame hashes now line up with aggregate backtest dataset hashes for the consumed materialized frame.
- Benchmark cache speedup is measured only for complete cold-build/warm-hit reuse with matching feature output hashes.

## Remaining Limitations

- The benchmark measures feature-build cache reuse only; it does not implement or claim persistent backtest execution caching.
- Feature materialization is local/offline and research-only; it is not promotion evidence.
- Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.
