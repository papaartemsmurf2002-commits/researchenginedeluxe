# Stage R106 Deterministic Archive Fixture Checksums Report

Date: 2026-06-20
Packet: `WPR106-376-deterministic-archive-fixture-checksums`

## Summary

WPR106-376 repairs a broad validation blocker in test fixture generation. Some
Binance Vision archive tests generated the ZIP payload once for the archive and
again for the `.CHECKSUM`; on Python versions that vary default ZIP member
metadata, those repeated calls can produce different bytes and fail checksum
validation before reaching the intended archive-quality assertion.

The fixture helpers now route through a deterministic ZIP payload helper with a
fixed member timestamp and stored compression. This keeps production checksum
validation strict while making repeated test fixture generation byte-stable.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py::test_archive_fixture_zip_payload_helper_is_byte_stable tests\tradingbotsuite\test_market_data_collection.py::test_collect_candidate_depth_public_archive_fixtures_rejects_duplicate_source_bars -q`
  - `2 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_engine.py::test_hyperliquid_stream_dedupes_duplicate_fills_across_channels -q -p no:cacheprovider`
  - `1 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite tests\integration -q -p no:cacheprovider`
  - `410 passed, 2 warnings`
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `git diff --check`
  - passed with existing LF-to-CRLF warnings only

The first broad rerun after the checksum fix hit Windows `WinError 10055`
during pytest-asyncio event-loop setup before the affected async test body ran.
The targeted async test passed on direct retry, and the full broad chunk then
passed.

## Boundary Statement

This packet changes test fixture generation only. It does not change production
archive download behavior, checksum validation, data-quality gates, sandbox
artifacts, strict-validation behavior, candidate-pack gates, paper/live
behavior, sizing, order placement, runtime mode, live configuration,
candidate-evidence semantics, or promotion state.
