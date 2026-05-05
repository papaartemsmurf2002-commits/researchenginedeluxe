# WPR26-01 Lower-Timeframe Candidate-Pack Gates

Status: closed
Owner: Codex Research Agent
Stage: Stage R26 lower-timeframe candidate-pack evidence gates
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Make lower-timeframe triple-barrier evidence durable at research candidate-pack time. WPR25 added cycle-level lower-timeframe execution and artifact evidence; this packet makes candidate-pack validation independently reject missing, mismatched, or ranking-only lower-timeframe claims.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR26-01-lower-timeframe-candidate-pack-gates.md`
- `docs/stage_reports/STAGE_R26_LOWER_TIMEFRAME_CANDIDATE_PACK_GATES_REPORT.md`
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `tests/research_artifacts/test_candidate_pack.py`
- `tests/live/test_preflight.py`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No changes to candidate generation, backtest execution, vector lower-timeframe support, or historical-cycle runner behavior.
- No candidate acceptance from synthetic or incomplete fixture evidence.

## Implementation plan

1. Detect lower-timeframe exit-policy candidates in durable candidate-pack validation.
2. Require fixture/source lower-timeframe evidence when such candidates are pack-eligible.
3. Recompute lower-timeframe evidence from `backtest_index.parquet` and per-backtest manifests.
4. Require sequence proof and exit price source counts for traded lower-timeframe rows.
5. Include lower-timeframe source evidence in research candidate-pack manifests and evidence summaries.

## Exit criteria

- Triple-barrier candidate packs are blocked if lower-timeframe source evidence is absent or incomplete.
- Triple-barrier candidate packs are blocked if any aggregate/split/stress backtest row omits lower-timeframe path/hash/cache identity.
- Triple-barrier candidate packs are blocked if traded rows lack lower-timeframe sequence proof counts.
- Fixed-holding candidate packs remain unaffected.
- Focused research-artifact tests, live preflight, compile, contracts, and diff check pass.

## Completion summary

- Added durable candidate-pack validation for lower-timeframe exit-policy candidates.
- Candidate packs now reject missing lower-timeframe source evidence, missing family/path/hash/row-count evidence, source hash mismatches, and missing lower-timeframe backtest-index columns.
- Backtest-index rows and per-backtest manifests are cross-checked for lower-timeframe path, hash, cache-key component, exit policy, and exit price source.
- Traded lower-timeframe rows must provide sequence-proof counts, barrier counts, and exit-price-source counts.
- Research candidate-pack manifests now carry lower-timeframe source evidence when present.
- Fixed-holding candidate-pack behavior remains unchanged.

## Validation evidence

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/research_artifacts/test_candidate_pack.py::test_research_candidate_pack_is_research_only_and_rejected_for_live_input tests/research_artifacts/test_candidate_pack.py::test_research_candidate_pack_includes_lower_timeframe_source_evidence tests/research_artifacts/test_candidate_pack.py::test_research_candidate_pack_blocks_lower_timeframe_without_source_evidence tests/research_artifacts/test_candidate_pack.py::test_research_candidate_pack_blocks_lower_timeframe_backtest_hash_mismatch tests/research_artifacts/test_candidate_pack.py::test_research_candidate_pack_blocks_missing_lower_timeframe_sequence_proof_counts -q
$env:PYTHONPATH='src'; python -m pytest tests/research_artifacts/test_candidate_pack.py tests/live/test_preflight.py -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

Results: compile passed, focused WPR26 tests passed with 5 tests, research-artifacts/live passed with 55 tests, contracts passed with 75 tests, and `git diff --check` reported line-ending warnings only.
