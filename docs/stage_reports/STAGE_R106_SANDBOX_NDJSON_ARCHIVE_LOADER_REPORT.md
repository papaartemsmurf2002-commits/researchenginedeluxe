# Stage R106 Sandbox NDJSON Archive Loader Report

Date: 2026-06-19
Packet: `WPR106-291-sandbox-ndjson-archive-loader`
Owner: Codex Research Agent
Status: closed

## Summary

WPR106-291 expands sandbox local archive intake to support `.ndjson` and
`.ndjson.gz` files. These formats are treated as aliases of the existing JSONL
newline-delimited JSON loader, so local stream exports from Hyperliquid,
Bybit, OKX, or local manifests can be loaded without renaming files.

This keeps the archive path deterministic and local-only while preserving the
existing 2024+ filter, venue alias normalization, descriptor source integrity,
and sandbox-only evidence boundaries.

## Implementation

- Added `.ndjson` dispatch to the existing JSONL market-data loader.
- Added `.ndjson.gz` dispatch to the existing gzip JSONL market-data loader.
- Added `.ndjson` and `.ndjson.gz` to archive manifest builder supported
  suffixes.
- Added regression coverage for direct NDJSON market loading, gzip NDJSON
  market loading, and gzip NDJSON archive manifest inclusion/source suffix
  reporting.

## Boundary

This packet only changes local sandbox market-data format intake. It does not
execute strict validation, write candidate packs, create paper/live signals,
define sizing, place orders, change runtime mode, write live configuration,
mutate source files, download provider data, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "ndjson"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 3 focused NDJSON tests passed.
- 137 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
