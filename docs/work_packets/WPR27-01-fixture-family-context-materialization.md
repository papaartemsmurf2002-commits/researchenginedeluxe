# WPR27-01 Fixture-Family Context Materialization

Status: closed
Owner: Codex Research Agent
Stage: Stage R27 fixture-family context materialization
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Materialize validated optional fixture-pack families into historical research-cycle feature inputs with point-in-time joins and provenance. The current runner consumes cycle datasets and lower-timeframe bars, but funding, premium, open-interest, and aggregate-trade context must be prejoined to be usable. This packet closes that gap for fixture-backed research cycles.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR27-01-fixture-family-context-materialization.md`
- `docs/stage_reports/STAGE_R27_FIXTURE_FAMILY_CONTEXT_MATERIALIZATION_REPORT.md`
- `src/tradingbotsuite/data/historical_fixture_pack.py`
- `src/tradingbotsuite/features/builders.py`
- `src/tradingbotsuite/features/cache.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `tests/contracts/test_historical_fixture_pack_contract.py`
- `tests/features/test_feature_builders.py`
- `tests/historical/test_full_cycle_local_fixture_pack.py`
- `tests/live/test_preflight.py`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No provider downloading or real data acquisition.
- No changes to strategy alpha logic or candidate acceptance thresholds.
- No lower-timeframe execution changes; WPR25/WPR26 already cover that path.

## Implementation plan

1. Extend fixture-pack validation payloads with optional family provenance for funding, premium, open interest, and aggregate trade families.
2. Add point-in-time fixture-family context materialization for fixture-backed cycle datasets using backward as-of joins by symbol and event time.
3. Record joined family paths, hashes, row counts, columns, and output context columns in data-source and feature-build manifests.
4. Include fixture-family provenance in feature cache identity so context changes invalidate feature artifacts.
5. Add tests for successful family context joins, lookahead prevention, provenance, cache invalidation, and default behavior without optional families.

## Exit criteria

- Fixture-backed cycles can consume optional funding/premium/open-interest/agg-trade families without prejoined cycle columns.
- As-of joins never use future family rows.
- Feature/cache manifests record family context provenance and joined columns.
- Changing optional family content changes feature cache identity.
- Existing cycles without optional families remain valid.
- Focused feature/fixture/historical tests, live preflight, compile, contracts, and diff check pass.

## Completion evidence

- Fixture-pack validation now surfaces `optional_context_families` provenance for funding, premium, open-interest, and aggregate-trade families with path, hash, row-count, columns, and event-time fields.
- Fixture-backed cycle loading materializes context families with backward as-of joins by `symbol` and event time before dataset hashing, feature building, and backtesting.
- Feature build and feature cache manifests now carry `fixture_family_context_sha256`, joined family lists, joined columns, and full materialization evidence.
- Cache identity includes fixture-family context provenance so context changes produce different feature cache keys.
- Validation:
  - `python -m compileall -q src/tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests\features\test_feature_builders.py tests\contracts\test_historical_fixture_pack_contract.py -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `git diff --check` completed with line-ending warnings only.
