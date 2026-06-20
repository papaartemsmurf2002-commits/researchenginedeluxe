# Stage R106 Sandbox ZIP JSON Member Loader Report

Date: 2026-06-19
Packet: `WPR106-292-sandbox-zip-json-member-loader`
Owner: Codex Research Agent
Status: closed

## Summary

WPR106-292 expands sandbox ZIP archive loading beyond CSV-only members. ZIP
files can now load TSV, JSON, JSONL, and NDJSON market-data members when no CSV
member is present, allowing local stream-style venue exports to remain zipped
for archive-backed sandbox iteration.

Existing CSV behavior is preserved: ZIPs with CSV members still prefer CSV
first, so Binance Vision kline ZIPs and headered venue-export CSV ZIPs keep the
same parsing path.

## Implementation

- Replaced the CSV-only ZIP reader with a deterministic ZIP table reader.
- Kept CSV as the first member-type priority, followed by TSV, JSON, JSONL, and
  NDJSON.
- Reused existing header-aware CSV/TSV parsing and JSON/JSONL/NDJSON parsing.
- Added regression coverage for ZIP NDJSON loading, CSV-priority behavior, and
  archive manifest inclusion of ZIP NDJSON content-derived descriptors.

## Boundary

This packet only changes local sandbox market-data ZIP member intake. It does
not execute strict validation, write candidate packs, create paper/live
signals, define sizing, place orders, change runtime mode, write live
configuration, mutate source files, download provider data, or claim promotion
readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "zip_ndjson or prefers_csv_zip or headered_zip or binance_vision_kline_zip"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 8 focused ZIP tests passed.
- 140 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
