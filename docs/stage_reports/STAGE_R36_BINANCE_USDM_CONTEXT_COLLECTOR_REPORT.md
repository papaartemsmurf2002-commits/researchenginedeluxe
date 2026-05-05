# Stage R36 Binance USD-M Context Collector Report

Date: 2026-05-04
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR36-01-binance-usdm-context-collector.md`
Status: closed

## Scope

WPR36 added a research-only Binance USD-M REST context collector for:

- `funding_rate`
- `premium_index`
- `open_interest`

The packet did not add TradingView support, live execution, promotion, order placement, automatic fixture-pack generation, or historical-cycle execution.

## Implementation Summary

- Added `collect_binance_usdm_context` in `src/tradingbotsuite/research/market_data.py`.
- Added a bounded REST fetcher for:
  - `/fapi/v1/fundingRate`
  - `/fapi/v1/premiumIndexKlines`
  - `/futures/data/openInterestHist`
- Normalized output rows include `source_name: binance_usdm_rest`, `symbol`, `data_family`, `source_row_index`, `event_time_ms`, and family-specific context fields.
- Manifests include deterministic content hashes, source hashes, row counts, endpoint metadata, receive-time limitations, and research-only boundary metadata.
- Added `collect-binance-context` CLI with bounded symbols, families, intervals, and live-mode rejection.
- Registered `collect-binance-context` in the research command registry.
- Extended fixture-builder accepted context sources to include `binance_usdm_rest` for funding, premium, and open-interest families.

## Review Fixes

Agent review identified one P1 compatibility issue:

- The collector manifest contained the literal legacy source name in a non-promotable note, and the fixture builder rejected that manifest as unsafe.

The note was rewritten to avoid embedding the legacy source string, and a regression test now feeds a real collector-emitted manifest into `build_provider_kline_fixture_pack`.

## Boundary Notes

- `binance_usdm_rest` is distinct from Binance Vision and is not mislabeled as archive data.
- Collected context rows are not live signals and are not promotion-ready.
- Receive timestamps are unavailable, so collected rows remain diagnostic and non-promotable.
- The command is a registered research command and is rejected in live mode.
- The collector can obtain data when explicitly run, but generated artifacts remain research-only inputs for fixture construction.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py tests\contracts\test_historical_fixture_pack_contract.py tests\live\test_preflight.py -q` passed: 67 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 97 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 26 tests.
- `git diff --check` reported only CRLF normalization warnings.

## Close Decision

Stage R36 is closed. The research branch now has a local provider path for collecting fresh Binance USD-M context manifests that can feed the context-aware fixture-pack builder without using legacy chart exports.
