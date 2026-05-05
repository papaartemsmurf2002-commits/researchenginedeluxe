# WPR35-01 Provider Context Fixture Pack Builder

Status: closed
Owner: Codex Research Agent
Stage: Stage R35 provider context fixture pack builder
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Extend the provider fixture-pack builder so a generated historical fixture pack can include already-local optional provider context manifests for funding rate, premium index, open interest, and aggregate trades. The builder must stay research-only, use no TradingView legacy inputs, perform no live/runtime writes, and fail closed on unsupported, synthetic, mismatched, or unverifiable context sources.

## Allowed paths

- `src/tradingbotsuite/data/historical_fixture_pack.py`
- `src/tradingbotsuite/main.py`
- `tests/contracts/test_historical_fixture_pack_contract.py`
- `tests/historical/test_full_cycle_local_fixture_pack.py`
- `tests/live/test_preflight.py`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR35-01-provider-context-fixture-pack-builder.md`
- `docs/stage_reports/STAGE_R35_PROVIDER_CONTEXT_FIXTURE_PACK_BUILDER_REPORT.md`

## Non-goals

- No TradingView export, Pine, or legacy parity input support.
- No provider download, network fetch, or live data collection in this packet.
- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital-allocation work.
- No fixture-pack schema version bump unless validation proves unavoidable.
- No lower-timeframe bar generation.

## Implementation plan

1. Add optional context manifest intake to the existing provider fixture-pack builder while preserving kline-only behavior as the default.
2. Normalize supported local context manifests into fixture family Parquet files with deterministic provenance columns and manifest hashes.
3. Reject TradingView, synthetic, unsupported family/source, symbol mismatch, hash mismatch, duplicate family, and missing required fields.
4. Add repeatable CLI `--context-manifest` support to `build-historical-fixture-pack`.
5. Add contract and full-cycle coverage proving generated context families validate and are materialized without prejoined cycle columns.
6. Record validation evidence and close the packet only after review and focused validation pass.

## Exit criteria

- Builder-generated fixture packs can include funding rate, premium index, open interest, and aggregate-trade context families from local provider manifests.
- Generated fixture manifests truthfully report included and omitted optional families.
- CLI output remains research-only, observe-only, and not promotion-ready.
- Existing kline-only builder behavior remains intact.
- Focused tests, compile, contracts, live preflight, and diff check pass.

## Completion evidence

- `build_provider_kline_fixture_pack` now accepts optional local `context_manifest_paths` for `funding_rate`, `premium_index`, `open_interest`, and `agg_trade`.
- The builder remains local-file only: it resolves existing manifest data paths, verifies declared hashes and row counts, and performs no network fetch or live runtime write.
- TradingView and synthetic provenance are rejected for source manifests, context manifests, context rows, and validated fixture-pack provenance.
- Context families are normalized to deterministic Parquet family files with explicit `data_family`, provider provenance, hashes, row counts, and research-only flags.
- Generated fixture manifests truthfully omit only absent optional families and expose context source records.
- Optional context validation now requires explicit matching `data_family` and supported materializable columns before a family is exposed as `optional_context_families`.
- CLI `build-historical-fixture-pack` now accepts repeatable `--context-manifest` arguments and still routes through live-mode research-command rejection.
- Full-cycle coverage proves builder-generated context families materialize into registered feature frames and feature-cache identity.
- Review found six P1 fail-closed issues during the packet; all were fixed and regression-tested before closure.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py tests\historical\test_full_cycle_local_fixture_pack.py -q` passed: 33 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 95 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 25 tests.
- `git diff --check` reported only pre-existing CRLF normalization warnings.
