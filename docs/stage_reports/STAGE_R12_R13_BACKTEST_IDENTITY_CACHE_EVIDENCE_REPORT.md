# Stage R12/R13 Backtest Identity Cache Evidence Report

Status: closed - identity-only backtest cache evidence hardened
Owner: Codex Research Agent
Date: 2026-05-04

## Scope

This wave completed a bounded backtest identity hardening slice:

- Backtest manifests now expose explicit identity-only cache policy fields.
- Backtest cache keys are auditable through nested `cache_key_components`.
- Lower-timeframe path relocation no longer changes cache identity when content hashes match.
- Lower-timeframe content changes alter backtest identity.
- Historical candidate rankings carry aggregate backtest cache key and result hash evidence.
- Historical benchmark reports include repeat consistency for backtest cache keys, result hashes, and ranking identity hashes.

## Research Boundary

All new artifacts remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

No persistent backtest execution-cache lookup, artifact reuse, paper, shadow, testnet, live, canary, order-placement, live-mode mutation, or promotion-ready candidate path was added. Benchmark output continues to report `backtest_cache_measured: false`.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_backtest_contracts.py tests/historical/test_full_cycle_synthetic.py tests/historical/test_research_cycle_benchmark.py -q` passed: 17 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed: 47 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/historical -q` passed: 8 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/backtesting tests/live/test_preflight.py -q` passed: 37 passed.
- `git diff --check` passed with only LF-to-CRLF warnings.

## Review Resolution

Reviewers found no blocking issues after the final patch:

- Engine identity policy fields are consistent and no execution-cache reuse path was added.
- `cache_key` is tested as the stable hash of declared components.
- Lower-timeframe path independence and content sensitivity are covered.
- Historical rankings carry aggregate backtest cache key/result hash evidence.
- Benchmarks preserve `backtest_cache_measured: false` and add repeat identity evidence only.

## Remaining Limitations

- This is identity evidence, not a persistent execution cache.
- `config_sha256` still records resolved audit paths and may differ under relocation; `cache_key` is the path-independent identity field.
- Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.
