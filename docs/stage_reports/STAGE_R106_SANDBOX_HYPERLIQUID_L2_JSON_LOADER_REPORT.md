# Stage R106 Sandbox Hyperliquid L2 JSON Loader Report

Date: 2026-06-19
Packet: `WPR106-294-sandbox-hyperliquid-l2-json-loader`
Owner: Codex Research Agent
Status: closed

## Summary

WPR106-294 expands sandbox local venue-export intake for Hyperliquid-style
nested `l2Book` JSON payloads. The sandbox loader now flattens local `levels`
arrays into deterministic best bid/ask price and size columns, then reuses the
existing bid/ask midpoint path to derive canonical `close` values.

The behavior applies to plain JSON, JSONL/NDJSON message rows, and ZIP JSON
members through the existing local file readers. Archive manifest build rows
record source-transformation metadata so agents can distinguish flattened book
snapshots from already-flat bid/ask exports.

## Implementation

- Added deterministic flattening for local Hyperliquid `l2Book` payloads with
  list or mapping `levels` side structures.
- Preserved outer message metadata such as `channel` when flattening nested
  `data` payloads.
- Emitted flat `bestBidPx`, `bestAskPx`, `bidSize`, `askSize`, optional order
  counts, and `l2BookFlattened` columns.
- Reused the existing bid/ask midpoint `close` derivation and 2024+ filtering.
- Added loader source-transformation metadata and archive manifest build-report
  fields for that metadata.
- Added `l2Book`/flattened book recognition to archive manifest data-family
  inference for generic local snapshot exports.
- Added focused tests for plain JSON loading, ZIP JSON loading, and archive
  manifest inclusion of nested Hyperliquid L2 book exports.

## Boundary

This packet only changes local sandbox market-data normalization and archive
manifest diagnostics. Nested book snapshots remain diagnostic archive inputs;
they are not strict L2 fill evidence, venue execution proof, candidate
evidence, paper/live signals, sizing, or promotion evidence.

No strict validation cycle was executed, no candidate pack was written, no
paper/live artifact was created, no orders were placed, no runtime mode or live
configuration was changed, no provider data was downloaded, and no source
archive file was mutated.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "l2_book_json or l2_book_zip_json or l2_book_jsonl_messages or hyperliquid_l2_book_json_export"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 4 focused Hyperliquid L2 JSON tests passed.
- 147 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
