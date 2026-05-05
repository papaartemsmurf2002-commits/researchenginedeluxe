# Stage R9/R10/R12 Research Completion Report

Status: closed - research completion foundations implemented
Owner: Codex Research Agent
Date: 2026-05-04

## Scope

This wave completed the bounded R9/R10/R12 foundations:

- R9 HMM/KNN diagnostics: explicit distance metadata, normalized distance aliases, reusable neighbor-pool selection, explicit regime-match modes, compatible-regime diagnostics, and feature-set variant identity in artifacts.
- R10 fixture packs: `historical-fixture-pack-manifest-v1` validation for offline local BTC fixture packs, including required research-only flags, cycle dataset path/hash/row count checks, required bars-family schema evidence, and historical-cycle loader integration.
- R12 benchmark gate: `benchmark-historical-research-cycle` command and report writer with small/medium tiers, runtime throughput, feature pass-through timing, memory peak, artifact overhead, deterministic repeat hash, and explicit cache-speedup non-measurement.

## Research Boundary

All new artifacts remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

No paper, shadow, testnet, or live execution was added. The new benchmark command is registered as a research command and is rejected by live preflight.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q` passed: 39 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_historical_fixture_pack_contract.py tests/historical/test_full_cycle_local_fixture_pack.py tests/historical/test_research_cycle_benchmark.py -q` passed: 8 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed: 44 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q` passed: 24 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/historical -q` passed: 8 passed.
- `git diff --check` passed with only LF-to-CRLF warnings.

## Review Resolution

Reviewers identified one P1, four P2, and one P3 risk during the packet. All were fixed before closure:

- Required fixture families now require path, hash, row count, and declared schema evidence.
- Historical-cycle aggregate inputs are sorted by bar time consistently with split evaluation.
- Benchmark repeat directories are cleaned before each run to prevent stale artifact overhead.
- Benchmark determinism tests use two repeats.
- Explicit KNN regime modes no longer conflict with legacy boolean diagnostics.
- Compatible-mode usage is counted by query row, not diagnostic neighbor row.
- Normalized Lorentzian aliases use the backend-aware Lorentzian path.

## Remaining Limitations

- Fixture-pack support validates offline local evidence, but it does not create a long-range real BTC evidence pack by itself.
- Benchmark cache speedup is intentionally reported as not measured because the historical research cycle has no persistent execution cache yet.
- Benchmark memory peak uses Python `tracemalloc`; it does not claim full process RSS or native allocator memory.
- Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.
