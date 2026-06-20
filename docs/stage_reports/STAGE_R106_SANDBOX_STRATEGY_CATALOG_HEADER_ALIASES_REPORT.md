# Stage R106 Sandbox Strategy Catalog Header Aliases Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-268-sandbox-strategy-catalog-header-aliases.md`
Status: closed

## Summary

WPR106-268 makes direct sandbox strategy catalogs easier to ingest from
existing spreadsheets by normalizing common human-friendly header aliases before
falling back to lead/proxy compilation.

## Implementation

- Added direct strategy catalog alias normalization in
  `tradingbotsuite.research_sandbox.intake`.
- Recognized aliases for hypothesis ID, family, signal column, side, source ID,
  exit profile, filter column/ranges, params, tags, and notes.
- Preserved canonical direct catalogs and existing spreadsheet-like lead proxy
  compilation.
- Expanded tag parsing to accept pipe, comma, or semicolon separators.
- Added focused sandbox tests for alias-heavy direct catalog loading and
  materialization.

## Boundary

The packet only improves local strategy catalog parsing for sandbox descriptor
intake. It does not execute sandbox sweeps, execute strict validation, write
candidate artifacts, change strategy math, create paper/live signals, define
sizing, place orders, mutate runtime mode, write live configuration, download
provider data, mutate source archive files, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "strategy_catalog"
# 10 passed, 88 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 98 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 460 passed, then known ISSUE-R106-026 WinError 10055 during pytest-asyncio
# event-loop socketpair setup before the affected async test body

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py -q -k "provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest"
# 1 passed, 41 deselected

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q -k "not provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest"
# 460 passed, 1 deselected
```

Repeated full one-shot contract attempts continued to hit known
`ISSUE-R106-026` at pytest-asyncio socketpair setup after 460 passing tests.

## Remaining Work

Direct catalog header aliases are covered for common existing spreadsheet
labels. Later packets can add more aliases if real local strategy sheets expose
additional stable header names.
