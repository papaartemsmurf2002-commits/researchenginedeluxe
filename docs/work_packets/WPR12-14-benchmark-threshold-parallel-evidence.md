# WPR12-14 Benchmark Threshold And Parallel Evidence

Status: closed
Owner: Codex Research Agent
Stage: Stage R12 benchmark threshold and parallel evidence
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Harden the historical research-cycle benchmark so Stage R12 evidence includes explicit regression thresholds and truthful parallel-speedup evidence. The benchmark must keep claims reproducible and scoped: historical-cycle throughput, memory, artifact overhead, feature-cache reuse, backtest identity consistency, and optimizer parallel evaluator speedup must be recorded as research-only evidence, without implying live readiness or persistent backtest execution-cache reuse.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR12-14-benchmark-threshold-parallel-evidence.md`
- `docs/stage_reports/STAGE_R12_BENCHMARK_THRESHOLD_PARALLEL_EVIDENCE_REPORT.md`
- `src/tradingbotsuite/research_cycle/benchmark.py`
- `src/tradingbotsuite/optimization/optimizer.py`
- `src/tradingbotsuite/optimization/search_space.py`
- `tests/historical/test_research_cycle_benchmark.py`
- `tests/optimization/test_parallel_results_equal_serial.py`
- `tests/live/test_preflight.py`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No persistent backtest execution-cache reuse.
- No claim that optimizer synthetic parallel speedup equals full historical-cycle backtest speedup.
- No large benchmark tier that would make routine validation slow.
- No broad rewrite of the historical-cycle runner.

## Implementation plan

1. Add benchmark regression thresholds per tier for runtime throughput, memory peak, artifact overhead, deterministic repeat consistency, and feature-cache reuse evidence.
2. Add threshold evaluation rows to the benchmark report with pass/fail status and failure reasons.
3. Add a deterministic optimizer parallel-speedup microbenchmark to the report, clearly scoped to optimizer candidate evaluator parallelism.
4. Keep historical-cycle backtest cache claims truthful: identity-only, no execution-cache lookup, no execution-cache hit.
5. Update tests to assert threshold evidence, parallel evidence scope, and research-only boundary fields.
6. Preserve existing benchmark command behavior and live preflight rejection.

## Exit criteria

- `benchmark-historical-research-cycle` reports regression threshold checks and an overall threshold pass flag.
- Benchmark reports include measured optimizer parallel evaluator speedup with deterministic serial/parallel result equivalence evidence.
- The report distinguishes optimizer parallel evidence from historical-cycle backtest parallelism.
- Feature-cache speedup and backtest identity evidence remain truthful.
- All artifacts remain `research_only`, `observe_only`, and `promotion_ready: false`.
- Focused tests, contracts, compileall, and diff checks pass.

## Risk controls

- Use conservative thresholds suitable for local repeatability, not marketing claims.
- Clearly label synthetic optimizer parallel evidence and do not claim full-cycle backtest parallelism.
- Keep dirty-tree edits confined to WPR12-14 allowed paths.
- Treat earlier uncommitted WPR files in the dirty tree as out of scope.

## Exit evidence

- Historical research-cycle benchmark reports now include a regression threshold policy and `benchmark_gate` with per-check status, observed values, comparators, thresholds, failure reasons, and skipped-evidence reasons.
- Repeat-dependent evidence no longer passes when skipped; `benchmark_gate.passed` requires no failed checks and no skipped required evidence.
- Benchmark gates now derive live fetch, order placement, backtest cache lookup/hit, and execution-cache reuse flags from cycle/backtest manifests.
- Memory threshold evidence is labeled as `python_tracemalloc_peak_bytes` and explicitly does not claim RSS or native allocator memory.
- Benchmark reports now include synthetic optimizer candidate-evaluator parallel evidence with repeated serial/parallel samples, median timings, possible active workers, result/stability-region equality hashes, and measured positive timing evidence.
- The benchmark distinguishes optimizer evaluator parallelism from historical-cycle backtest parallelism and keeps persistent backtest execution-cache reuse out of scope.
- Tests cover successful repeat=2 evidence, repeat=1 incomplete evidence, and a negative gate payload that fails thresholds.
- Reviewer rechecks reported no remaining benchmark-semantics or research-boundary findings after fixes.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/historical/test_research_cycle_benchmark.py tests/optimization/test_parallel_results_equal_serial.py tests/live/test_preflight.py -q` passed: 31 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed: 59 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/historical tests/optimization -q` passed: 23 passed.
- `git diff --check` passed with only existing LF-to-CRLF warnings.
