# Stage R29 Benchmark CLI Gate Completeness Report

Date: 2026-05-04

## Scope

WPR29 hardened the historical research-cycle benchmark CLI so a failed or evidence-incomplete `benchmark_gate` cannot silently appear as a successful command result.

This is research-only benchmark guardrail work. It makes no live, paper, shadow, testnet, canary, promotion, order-placement, capital-allocation, or profit/performance claim.

## Changes

- `src/tradingbotsuite/main.py`
  - Derives benchmark tier choices from `BENCHMARK_TIERS`.
  - Changes `benchmark-historical-research-cycle --repeat` default to `2`.
  - Adds `--allow-failed-gate` for deliberate report-only failed-gate output.
  - Reads the generated benchmark report and returns gate fields in the CLI payload.
  - Raises a clear `benchmark_historical_research_cycle_gate_failed` error when the gate fails and no override is supplied.

- `tests/historical/test_research_cycle_benchmark.py`
  - Adds lightweight CLI tests for failed-gate default behavior, override behavior, passed-gate payload fields, and medium-tier registry coverage.
  - Keeps the full small-tier benchmark report test as the strict benchmark evidence check.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_research_cycle_benchmark.py tests\live\test_preflight.py -q` passed: 31 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 76 tests.
- `git diff --check` completed with line-ending warnings only.

## Result

WPR29 is complete. Benchmark CLI behavior now matches the benchmark report gate: default CLI usage fails closed on incomplete evidence, while report-only failed-gate output requires an explicit override.
