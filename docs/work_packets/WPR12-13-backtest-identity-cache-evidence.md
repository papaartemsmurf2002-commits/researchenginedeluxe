# WPR12-13 Backtest Identity Cache Evidence

Status: closed
Owner: Codex Research Agent
Stage: Stage R12/R13 backtest identity cache evidence
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Harden backtest cache-key identity evidence without implementing or implying persistent execution-cache reuse. Backtest manifests must expose deterministic identity components and explicit identity-only cache policy fields. Historical-cycle rankings and benchmark reports must carry repeatable backtest identity evidence while keeping `backtest_cache_measured: false`.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR12-13-backtest-identity-cache-evidence.md`
- `docs/stage_reports/STAGE_R12_R13_BACKTEST_IDENTITY_CACHE_EVIDENCE_REPORT.md`
- `src/tradingbotsuite/backtesting/engine.py`
- `src/tradingbotsuite/research_cycle/benchmark.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `tests/contracts/test_backtest_contracts.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `tests/historical/test_research_cycle_benchmark.py`

## Non-goals

- No persistent backtest artifact reuse or execution-cache shortcut.
- No live, paper, shadow, testnet, or canary execution.
- No promotion-ready candidate acceptance.
- No vectorized engine implementation.
- No change to trading decisions or execution simulation semantics.

## Implementation plan

1. Add explicit backtest manifest cache policy fields: identity-only, lookup disabled, hit false, and reuse disabled.
2. Add nested cache-key components to backtest manifests and make lower-timeframe path relocation not affect reproducible config identity when content hash is unchanged.
3. Carry aggregate backtest `cache_key` and `result_sha256` into candidate rankings as identity evidence.
4. Add benchmark repeat identity consistency over backtest cache keys and result hashes while preserving `backtest_cache_measured: false`.
5. Add focused tests for manifest policy fields, cache-key stability, lower-timeframe path independence, ranking identity columns, and benchmark repeat identity evidence.

## Exit criteria

- Backtest manifests make clear that no execution cache lookup/reuse occurred.
- Backtest cache-key components are auditable from the manifest.
- Backtest cache keys remain stable under run/output path relocation and lower-timeframe path relocation when content hashes match.
- Historical rankings expose aggregate backtest identity evidence.
- Benchmark reports identity repeat consistency but do not claim backtest cache speedup.
- Focused tests, contracts, compileall, and `git diff --check` pass.

## Risk controls

- Treat cache fields as identity/audit evidence only.
- Do not load prior backtest outputs as a shortcut.
- Keep all artifacts `research_only: true`, `observe_only: true`, and `promotion_ready: false`.
- Any real execution-cache reuse must be a later packet with explicit validation and speed benchmark evidence.

## Exit evidence

- Backtest manifests now expose `cache_policy`, `cache_lookup_used`, `cache_hit`, `execution_cache_reuse_enabled`, and nested `cache_key_components`.
- `cache_key` is the stable hash of the declared `cache_key_components`.
- Lower-timeframe paths remain in audit manifests but no longer affect reproducible cache identity when content hashes match.
- Lower-timeframe content changes alter the lower-timeframe hash and backtest cache key.
- Candidate rankings now carry aggregate backtest `cache_key`, `result_sha256`, identity scope, cache policy, and no-cache-reuse flags.
- Benchmarks now report repeat consistency for backtest cache keys, result hashes, and ranking identity hashes while keeping `backtest_cache_measured: false`.
- Review agents rechecked engine identity, historical-cycle identity, and benchmark repeat evidence and reported no blocking findings.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_backtest_contracts.py tests/historical/test_full_cycle_synthetic.py tests/historical/test_research_cycle_benchmark.py -q` passed: 17 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed: 47 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/historical -q` passed: 8 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/backtesting tests/live/test_preflight.py -q` passed: 37 passed.
- `git diff --check` passed with only existing LF-to-CRLF warnings.
