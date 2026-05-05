# Stage R5/R12 Optimizer Stability Truthfulness Report

Status: closed - optimizer stability evidence and gate truthfulness hardened
Owner: Codex Research Agent
Date: 2026-05-04

## Scope

This wave completed a bounded optimizer/stability hardening slice:

- Optimizer reports now include per-run cache telemetry for hits, misses, writes, hit rate, and cache size.
- Optimizer evaluation deduplicates candidate configs before serial or parallel execution.
- Stability regions deduplicate candidate IDs and expose validation coverage fields.
- Validation-required stability rejects aggregate-only and mixed-validation neighborhoods as incomplete.
- Historical-cycle rankings distinguish aggregate rank from optimizer rank and expose validation counts.
- `stability_evaluated` now means split/cost-stress-enriched stability, not aggregate-only neighborhood analysis.
- Historical cycles write `candidate_gate_report.parquet` for every candidate.
- Candidate pack gates require row-level validation flags, complete validation counts, durable gate-report evidence, and a validated accepted stability-region artifact.

## Research Boundary

All new artifacts remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

No persistent backtest execution-cache reuse, paper, shadow, testnet, live, canary, order-placement, live-mode mutation, or promotion-ready candidate path was added.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/optimization tests/historical/test_full_cycle_synthetic.py tests/research_artifacts/test_candidate_pack.py -q` passed: 25 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed: 44 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/optimization tests/historical tests/research_artifacts -q` passed: 29 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q` passed: 24 passed.
- `git diff --check` passed with only LF-to-CRLF warnings.

## Review Resolution

Reviewers identified multiple P1/P2 evidence risks during the packet. All were fixed before closure:

- Non-shortlisted rankings are no longer marked as fully stability evaluated.
- Stability regions now reject incomplete validation when validation evidence is required.
- Mixed validated-center/aggregate-neighbor regions are rejected instead of overclaimed.
- Candidate-gate evidence is materialized for every candidate.
- Pack gates now verify durable gate and stability artifacts, not only ranking row flags.
- Gate reports now apply the same stability-region blockers as the pack gate before setting `pack_eligible`.

## Remaining Limitations

- Optimizer cache telemetry is in-memory identity evidence only; it is not persistent execution-cache reuse.
- Region geometry still uses the current normalized-distance foundation, not a full search-space-aware connected-component optimizer.
- Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.
