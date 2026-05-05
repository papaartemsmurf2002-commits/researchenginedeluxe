# WPR5-12 Optimizer Stability Truthfulness

Status: closed
Owner: Codex Research Agent
Stage: Stage R5/R12 optimizer stability truthfulness and cache evidence
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Harden the research-cycle optimizer/stability evidence without introducing live behavior or fake execution-cache reuse. Rankings and stability-region artifacts must distinguish aggregate-only neighborhood analysis from split/cost-stress-enriched stability evidence, and optimizer cache reports must expose deterministic hit/miss evidence.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR5-12-optimizer-stability-truthfulness.md`
- `docs/stage_reports/STAGE_R5_R12_OPTIMIZER_STABILITY_TRUTHFULNESS_REPORT.md`
- `src/tradingbotsuite/optimization/cache.py`
- `src/tradingbotsuite/optimization/optimizer.py`
- `src/tradingbotsuite/optimization/stability.py`
- `src/tradingbotsuite/optimization/__init__.py`
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `tests/optimization/test_candidate_cache_keys.py`
- `tests/optimization/test_parallel_results_equal_serial.py`
- `tests/optimization/test_region_of_stability.py`
- `tests/optimization/test_spike_candidate_rejected.py`
- `tests/optimization/test_plateau_candidate_ranked_above_spike.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/research_artifacts/test_candidate_pack.py`

## Non-goals

- No persistent backtest execution-cache reuse.
- No live, paper, shadow, testnet, or canary execution.
- No promotion-ready candidate acceptance.
- No vectorized engine implementation.
- No large benchmark tier or parallel process-worker implementation.

## Implementation plan

1. Add optimizer cache telemetry for deterministic hits, misses, writes, and cache keys without changing evaluator semantics.
2. Extend optimization reports with cache telemetry and multiple-comparison warning metadata.
3. Extend stability regions with evaluation coverage fields so aggregate-only regions cannot be mistaken for fully validated stability evidence.
4. Update historical-cycle rankings so `stability_evaluated` means split/cost-stress-enriched stability, while aggregate neighborhood analysis remains separately visible.
5. Materialize per-candidate gate reports and require validated stability evidence before pack eligibility.
6. Add tests for cache telemetry, truthful stability flags, stability-region validation scope, and gate evidence.

## Exit criteria

- Non-shortlisted historical-cycle rankings are not marked as fully stability evaluated.
- Stability-region rows expose validation enrichment counts and reject incomplete validation as non-acceptance evidence.
- Optimizer reports include deterministic cache hit/miss/write telemetry.
- Candidate gate evidence is written for every candidate, and pack gates require validated stability evidence.
- Focused optimization/historical tests, contracts, compileall, and `git diff --check` pass.

## Risk controls

- Keep all artifacts `research_only: true`, `observe_only: true`, and `promotion_ready: false`.
- Do not reuse backtest artifacts as an execution cache.
- Preserve deterministic serial/parallel optimizer results.
- Treat cache telemetry as evidence only, not as a performance claim unless a benchmark measures it.

## Exit evidence

- Optimizer cache telemetry now records per-run hits, misses, writes, hit rate, and cache size without claiming persistent backtest reuse.
- Optimizer evaluation deduplicates candidate configs before serial or parallel execution, preventing duplicate candidates from inflating results or racing through the evaluator.
- Stability regions now deduplicate candidate IDs, expose validation coverage, and reject aggregate-only or mixed-validation neighborhoods when validation evidence is required.
- Historical-cycle rankings now separate `aggregate_rank` from `optimizer_rank`, expose validation counts, and reserve `stability_evaluated` for split/cost-stress-enriched stability.
- Historical cycles write `candidate_gate_report.parquet` for every candidate.
- Research candidate pack gates now require row flags, validation counts, durable gate-report evidence, and a validated accepted stability-region artifact.
- Review agents rechecked optimizer/stability, cache-evidence, runner/gate, and durable gate-report fixes and reported no blocking findings.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/optimization tests/historical/test_full_cycle_synthetic.py tests/research_artifacts/test_candidate_pack.py -q` passed: 25 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed: 44 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/optimization tests/historical tests/research_artifacts -q` passed: 29 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q` passed: 24 passed.
- `git diff --check` passed with only existing LF-to-CRLF warnings.
