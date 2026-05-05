# WPR34-01 Fixture Source Provenance Propagation

Status: closed
Owner: Codex Research Agent
Stage: Stage R34 fixture source provenance propagation
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Propagate validated historical fixture-pack source provenance into historical-cycle manifests and research candidate-pack source evidence, so downstream artifacts can audit provider, derivation, optional-family omissions, and research limitations without reopening the fixture manifest.

## Allowed paths

- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `tests/historical/test_full_cycle_local_fixture_pack.py`
- `tests/research_artifacts/test_candidate_pack.py`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR34-01-fixture-source-provenance-propagation.md`
- `docs/stage_reports/STAGE_R34_FIXTURE_SOURCE_PROVENANCE_PROPAGATION_REPORT.md`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No provider download or data collection.
- No fixture-pack schema version bump.
- No broad candidate-pack gate refactor.

## Implementation plan

1. Include fixture-pack `source`, `derivation`, `fixture_scope`, `omitted_optional_families`, and `research_evidence_limitations` in historical-cycle `data_source` payloads.
2. Add candidate-pack source evidence fields that summarize embedded fixture provenance and verify embedded-vs-manifest consistency where possible.
3. Add full-cycle coverage for checked-in BTCUSDT provenance propagation.
4. Add candidate-pack coverage for provenance summary and mismatch detection.
5. Record validation evidence and close the packet.

## Exit criteria

- Historical-cycle manifests expose fixture source and derivation provenance.
- Candidate-pack source evidence exposes the same provenance and reports whether embedded source/derivation matches the fixture manifest.
- Existing candidate-pack eligibility remains fail-closed.
- Focused tests, compile, contracts, live preflight, and diff check pass.

## Completion evidence

- Historical-cycle `data_source` payloads now include fixture scope, source, derivation, omitted optional families, and research evidence limitations copied from validated fixture-pack manifests.
- Research candidate-pack source evidence now includes embedded and fixture-manifest provenance summaries plus match flags.
- Candidate-pack gate fails closed on missing or mismatched fixture source, derivation, scope, omitted optional families, and research evidence limitations.
- Checked-in BTCUSDT full-cycle coverage asserts propagated provider provenance and limitation fields.
- Candidate-pack tests cover happy-path provenance, missing embedded provenance, and tampered source/derivation/scope/omission/limitation fields.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts\test_candidate_pack.py tests\historical\test_full_cycle_local_fixture_pack.py -q` passed: 41 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 83 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 25 tests.
- `git diff --check` reported only pre-existing CRLF normalization warnings.
- Review found two P1 fail-closed gaps; both were fixed and regression-tested before closure.
