# Stage R106 Sandbox Venue Price Aliases Report

Date: 2026-06-19
Packet: `WPR106-293-sandbox-venue-price-aliases`
Owner: Codex Research Agent
Status: closed

## Summary

WPR106-293 expands sandbox venue-export normalization for common OKX, Bybit,
Hyperliquid, and local archive price fields. The sandbox loader now accepts
mark/index/mid price aliases such as `markPx`, `idxPx`, and `midPx` as
canonical `close` sources.

When no explicit close-like price alias is present, book-style exports with
bid/ask price columns can derive canonical `close` from the bid/ask midpoint.
The derivation is recorded in normalization metadata and archive manifest build
rows so agents can distinguish explicit price sources from book-derived
midpoints.

## Implementation

- Added common mark/index/mid price aliases to the canonical close alias set.
- Added bid/ask price aliases and deterministic midpoint close derivation.
- Preserved explicit close-like aliases as the preferred path before midpoint
  fallback.
- Tightened Binance kline column assignment so headered book exports with six
  or more columns are not mistaken for headerless Binance kline rows.
- Added `derived_columns` and `derived_count` metadata to archive manifest
  build rows.
- Added regression coverage for OKX mark/index aliases, Hyperliquid/Bybit-style
  bid/ask midpoint snapshots, and archive manifest inclusion of L2 book
  snapshot exports.

## Boundary

This packet only changes local sandbox market-data normalization. It does not
execute strict validation, write candidate packs, create paper/live signals,
define sizing, place orders, change runtime mode, write live configuration,
mutate source files, download provider data, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "mark_and_index or bid_ask_midpoint or l2_bid_ask"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 3 focused venue price-alias tests passed.
- 143 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
