# Stage R33 Provider Kline Fixture Pack Builder Report

Date: 2026-05-04
Packet: `docs/work_packets/WPR33-01-provider-kline-fixture-pack-builder.md`
Status: complete

## Summary

Stage R33 adds a reproducible research-only builder for compact historical fixture packs from local provider kline manifests. This removes the need for ad hoc fixture-pack generation scripts and keeps TradingView exports out of the active research fixture path.

## Implementation

- Added `build_provider_kline_fixture_pack()` to `src/tradingbotsuite/data/historical_fixture_pack.py`.
- Added `ProviderKlineFixturePackBuildResult` with a CLI-friendly research-only payload.
- Added CLI command `build-historical-fixture-pack`.
- Registered `build-historical-fixture-pack` in the research command registry so live preflight rejects it.
- Added tests for Binance USD-M kline cache manifests, provider JSONL kline manifests, CLI output, generated manifest validation, TradingView rejection, synthetic provenance rejection, and row interval mismatch rejection.

## Research Boundary

The builder:

- consumes only already-local provider manifests and data files;
- performs no network fetch/download;
- writes `research_only: true`, `observe_only: true`, and `promotion_ready: false`;
- rejects TradingView provenance;
- rejects synthetic provenance anywhere in the source manifest;
- rejects unsupported source/family pairs;
- validates the generated fixture-pack manifest before returning.

Generated compact packs remain contract/full-cycle fixtures only. They are not OOS, stress, profitability, promotion, or performance evidence.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py tests\live\test_preflight.py -q` passed: 38 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 83 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py tests\live\test_preflight.py -q` passed: 32 tests.
- CLI smoke against `data\research\chart_ohlcv_cache\BTCUSDT_15m_1760450400000_1776178800000.manifest.json` passed and wrote a validated 12-row temp fixture pack.
- `git diff --check` reported only pre-existing CRLF normalization warnings.

## Review

Review identified two issues before closure:

- Synthetic provenance outside `source` could pass the builder.
- Row-level intervals were not checked against manifest interval.

Both issues were fixed and covered by regression tests.

## Decision

Stage R33 is complete. Continue research-only development. This stage improves reproducibility for local historical fixtures but does not change empirical acceptance or Stage 13 execution readiness.
