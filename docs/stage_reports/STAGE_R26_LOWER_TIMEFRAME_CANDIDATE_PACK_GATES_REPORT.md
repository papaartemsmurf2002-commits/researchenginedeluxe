# Stage R26 Lower-Timeframe Candidate-Pack Gates Report

Date: 2026-05-04
Owner: Codex Research Agent
Status: closed

## Scope

Stage R26 made WPR25 lower-timeframe triple-barrier evidence durable at research candidate-pack time. Candidate-pack validation now recomputes lower-timeframe source, backtest identity, manifest, and sequence-proof evidence instead of trusting rankings alone.

No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work was performed. All artifacts remain research-only, observe-only, and not promotion-ready.

## Changes

- Added lower-timeframe exit-policy detection for `triple_barrier` and `triple_barrier_atr` candidates.
- Added durable source checks for lower-timeframe family presence, path existence, SHA-256 verification, and row-count evidence.
- Added backtest-index checks for lower-timeframe required/used flags, path/hash/cache-key component, exit price source, sequence proof counts, barrier counts, and price-source counts.
- Added per-backtest manifest checks for exit policy, exit price source, lower-timeframe path/hash, and cache-key component agreement.
- Added lower-timeframe source evidence into research candidate-pack manifests when present.
- Preserved fixed-holding candidate-pack behavior.

## Validation

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/research_artifacts/test_candidate_pack.py::test_research_candidate_pack_is_research_only_and_rejected_for_live_input tests/research_artifacts/test_candidate_pack.py::test_research_candidate_pack_includes_lower_timeframe_source_evidence tests/research_artifacts/test_candidate_pack.py::test_research_candidate_pack_blocks_lower_timeframe_without_source_evidence tests/research_artifacts/test_candidate_pack.py::test_research_candidate_pack_blocks_lower_timeframe_backtest_hash_mismatch tests/research_artifacts/test_candidate_pack.py::test_research_candidate_pack_blocks_missing_lower_timeframe_sequence_proof_counts -q
$env:PYTHONPATH='src'; python -m pytest tests/research_artifacts/test_candidate_pack.py tests/live/test_preflight.py -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

Results:

- Compile: passed.
- Focused WPR26 tests: 5 passed.
- Research-artifacts/live: 55 passed.
- Contracts: 75 passed.
- `git diff --check`: line-ending warnings only.

## Decision

Stage R26 is closed. Lower-timeframe triple-barrier research candidates cannot be packed unless source evidence, backtest identity, and sequence-proof evidence are complete and internally consistent.
