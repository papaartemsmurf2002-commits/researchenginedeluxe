# Stage R106 Sandbox Venue Export Normalizer Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-243-sandbox-venue-export-normalizer.md`
Status: closed

## Summary

WPR106-243 makes local OKX, Bybit, and Hyperliquid archive-backed sandbox
iteration less brittle by normalizing common venue export column aliases into
the canonical sandbox market-frame schema.

## Implementation

- Extended `src/tradingbotsuite/research_sandbox/market_data.py` with
  conservative alias detection.
- Canonical output columns remain `timestamp`, `open`, `high`, `low`, `close`,
  and `volume`.
- Supported timestamp aliases include `ts`, `time`, `startTime`, `open_time`,
  and related variants.
- Supported price aliases include OKX short OHLCV fields (`o`, `h`, `l`, `c`),
  Bybit price fields (`openPrice`, `highPrice`, `lowPrice`, `closePrice`), and
  Hyperliquid trade fields (`px`, `sz`).
- Original columns are preserved when safe, so strategy feature columns remain
  available.
- The Binance Vision no-header fallback now avoids renaming files that already
  contain recognizable venue timestamp and price aliases.
- Archive manifest build rows and archive descriptor audit rows now include
  alias metadata: `alias_columns`, `alias_count`, and
  `assigned_binance_kline_columns`.
- The existing 2024+ filter and fail-closed missing timestamp/close behavior
  are preserved.

## Boundary

This packet only normalizes local sandbox market-frame inputs. It does not
download data, execute strict validation, write candidate packs, create
paper/live signals, define sizing, place orders, mutate runtime mode, write
live configuration, or claim promotion readiness.

## Validation

Focused validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 65 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed
```

Contract baseline attempt:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 460 passed, 1 pytest-asyncio setup error
```

The baseline failure occurred before the affected async contract test body ran:
Windows failed to create the event-loop `socket.socketpair()` with
`WinError 10055`. `ISSUE-R106-026` tracks this local validation-environment
blocker.

## Remaining Work

This packet does not add new network downloaders or account-connected venue
adapters. Future venue expansion should keep using local archive manifests and
research-only metadata unless a later approved packet explicitly scopes durable
provider intake.
