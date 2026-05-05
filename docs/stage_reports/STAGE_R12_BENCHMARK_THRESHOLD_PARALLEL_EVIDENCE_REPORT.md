# Stage R12 Benchmark Threshold And Parallel Evidence Report

Status: closed - benchmark threshold and parallel evidence hardened
Owner: Codex Research Agent
Date: 2026-05-04

## Scope

This wave completed a bounded Stage R12 benchmark hardening slice:

- Historical research-cycle benchmark reports now include a regression threshold policy and a `benchmark_gate`.
- Threshold checks record check IDs, metrics, observed values, comparators, thresholds, status, and failure reasons.
- Required repeat evidence is explicit: repeat-one benchmark reports are written, but `benchmark_gate.passed` is false and `evidence_complete` is false when repeat-dependent checks are skipped.
- Benchmark reports derive live fetch, order placement, backtest cache lookup/hit, and execution-cache reuse claims from actual cycle/backtest manifests.
- Memory evidence is labeled as `python_tracemalloc_peak_bytes`, with explicit non-claims for RSS and native allocator memory.
- Reports include a synthetic optimizer candidate-evaluator parallel microbenchmark with repeated serial/parallel samples, median timings, possible active worker count, positive timing evidence, and serial/parallel result and stability-region equality hashes.
- Optimizer parallel evidence is labeled as synthetic evaluator parallelism, not historical-cycle backtest parallelism or CPU/process scaling.

## Path Audit

WPR12-14-specific edits were confined to the packet's allowed paths:

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR12-14-benchmark-threshold-parallel-evidence.md`
- `docs/stage_reports/STAGE_R12_BENCHMARK_THRESHOLD_PARALLEL_EVIDENCE_REPORT.md`
- `src/tradingbotsuite/research_cycle/benchmark.py`
- `tests/historical/test_research_cycle_benchmark.py`

The working tree still contains many earlier uncommitted WPR files and modifications already represented in the ledger. Those prior packet changes are out of scope for this WPR12-14 closure and were not reverted or normalized.

## Research Boundary

All new benchmark evidence remains:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

No live, paper, shadow, testnet, canary, order-placement, live-mode mutation, promotion-ready candidate path, or persistent backtest execution-cache reuse was added. The benchmark command remains a registered research command and is covered by live preflight rejection.

## Review Resolution

Read-only reviewers identified and rechecked these issues:

- Repeat-one reports could pass despite skipped required evidence. Resolved by making skipped required evidence keep `benchmark_gate.passed` false.
- Safety/cache claims were hardcoded. Resolved by deriving live/order/cache flags from cycle and backtest manifests.
- Memory threshold evidence looked like total process memory. Resolved by renaming the gate to `tracemalloc_memory_peak_bytes` and adding non-RSS measurement metadata.
- Parallel-speedup pass/fail was timing brittle. Resolved by recording observed speedup while gating only on positive measured timings plus serial/parallel result and stability-region equivalence.

Final reviewer rechecks reported no remaining benchmark-semantics or research-boundary findings.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/historical/test_research_cycle_benchmark.py tests/optimization/test_parallel_results_equal_serial.py tests/live/test_preflight.py -q` passed: 31 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed: 59 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/historical tests/optimization -q` passed: 23 passed.
- `git diff --check` passed with only existing LF-to-CRLF warnings.

## Remaining Limitations

- The historical-cycle runner itself is still serial; the new parallel evidence is scoped to optimizer candidate evaluator parallelism only.
- The optimizer parallel microbenchmark uses a synthetic sleep-bound evaluator and should not be read as CPU-bound backtest scaling evidence.
- Memory evidence uses Python `tracemalloc` and does not measure RSS, native allocator memory, or external process memory.
- Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.
