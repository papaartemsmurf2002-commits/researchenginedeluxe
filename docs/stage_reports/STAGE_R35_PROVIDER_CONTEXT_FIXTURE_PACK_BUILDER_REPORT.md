# Stage R35 Provider Context Fixture Pack Builder Report

Date: 2026-05-04
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR35-01-provider-context-fixture-pack-builder.md`
Status: closed

## Scope

WPR35 extended the local provider fixture-pack builder so compact historical research fixture packs can include already-local optional provider context families:

- `funding_rate`
- `premium_index`
- `open_interest`
- `agg_trade`

The packet did not add TradingView support, provider downloads, lower-timeframe generation, live execution, promotion, paper, shadow, testnet, or runtime configuration writes.

## Implementation Summary

- `build_provider_kline_fixture_pack` now accepts `context_manifest_paths`.
- Local context manifests are resolved through existing file paths only and are checked for declared SHA-256 and row-count consistency.
- Supported context sources are bounded by family:
  - funding rate: Binance Vision, Crypto Lake
  - premium index: Binance Vision
  - open interest: Binance Vision, Crypto Lake
  - aggregate trades: Binance Vision, Crypto Lake
- Context rows are normalized to deterministic fixture-family Parquet files with explicit provider provenance, `data_family`, event time, hash, row count, and research-only flags.
- Aggregate trades are grouped by symbol and event time and can derive signed imbalance from buy/total or buy/sell quote-volume evidence.
- Generated manifests now include context source records and omit only optional families that were not supplied.
- The `build-historical-fixture-pack` CLI now supports repeatable `--context-manifest` arguments.
- Fixture-pack validation was hardened so unsafe or unusable optional context cannot be claimed as materialized context evidence.

## Review Fixes

Agent review identified six P1 fail-closed issues during implementation:

- unsafe fixture provenance could validate when hand-authored;
- unsafe context row provenance could pass through a clean manifest;
- kline source row-count mismatch was not rejected;
- optional context families could be exposed without usable materializer columns;
- top-level unsafe fixture provenance still validated after the first fix;
- optional context `data_family` was not required explicitly.

All six were fixed before closure and have regression tests in `tests/contracts/test_historical_fixture_pack_contract.py`.

## Boundary Notes

- TradingView remains legacy and is rejected as source, context, row-level provenance, and validated fixture provenance.
- Generated artifacts are `research_only`, `observe_only`, and `promotion_ready: false`.
- The command remains registered as a research command and is rejected by live preflight.
- Generated context evidence is suitable for contract/full-cycle execution and feature-cache identity, not OOS acceptance or performance claims.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py tests\historical\test_full_cycle_local_fixture_pack.py -q` passed: 33 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 95 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 25 tests.
- `git diff --check` reported only CRLF normalization warnings.

## Close Decision

Stage R35 is closed. The research branch can now generate compact, reproducible fixture packs that include local provider context families without relying on TradingView exports or synthetic context.
