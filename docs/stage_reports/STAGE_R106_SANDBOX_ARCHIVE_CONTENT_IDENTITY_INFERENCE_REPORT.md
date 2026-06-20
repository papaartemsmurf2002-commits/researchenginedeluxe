# Stage R106 Sandbox Archive Content Identity Inference Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-267-sandbox-archive-content-identity-inference.md`
Status: closed

## Summary

WPR106-267 reduces manual archive manifest setup for local OKX, Bybit, and
Hyperliquid exports by inferring descriptor identity from file content when
paths are generic.

## Implementation

- Extended sandbox archive manifest inference for venue, symbol, data family,
  and interval to use common content columns when overrides and path tokens do
  not provide enough identity.
- Added content parsing for venue/exchange/provider/source, symbol/instrument,
  coin/base/quote, interval/bar/timeframe, and channel/type/data-family hints.
- Added build-report row fields for venue, symbol, data-family, and interval
  inference source: override, path, content, content columns, default, or
  missing.
- Preserved source integrity, 2024+ filtering, deterministic descriptor IDs,
  and sandbox boundary flags.

## Boundary

The packet only improves local archive manifest construction from already
available local files. It does not download provider data, execute sandbox
sweeps, execute strict validation, write candidate artifacts, create paper/live
signals, define sizing, place orders, mutate runtime mode, write live
configuration, mutate source archive files, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "archive_manifest_builder"
# 4 passed, 92 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 96 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 460 passed, then known ISSUE-R106-026 WinError 10055 during pytest-asyncio
# event-loop socketpair setup before the affected async test body

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py -q -k "provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest"
# failed at the same known pytest-asyncio socketpair setup point

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q -k "not provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest"
# 460 passed, 1 deselected
```

## Remaining Work

Content-derived identity now covers common generic local archive exports.
Later packets can add provider-specific manifest templates if real local drops
show additional stable column names.
