# Stage R106 Sandbox Header-Aware ZIP Loader Report

Date: 2026-06-19
Packet: `WPR106-289-sandbox-header-aware-zip-loader`
Owner: Codex Research Agent
Status: closed

## Summary

WPR106-289 makes sandbox ZIP CSV loading header-aware. Headered local
venue-export CSV members inside ZIP files now preserve their source columns for
normalization and archive-manifest content inference, while existing Binance
Vision headerless kline ZIP support remains intact.

The packet also tightens archive data-family path inference so generic names
such as `market_export.zip` no longer falsely infer `mark_index` from the word
`market`.

## Implementation

- ZIP CSV members now pass through the same text-table header detection used
  by plain CSV inputs.
- File-like fallback reads rewind before retrying as headerless CSV.
- Headerless Binance Vision ZIP kline behavior remains covered.
- Headered ZIP venue-export columns can drive alias normalization and
  content-derived venue/symbol/interval/data-family inference.
- Archive data-family path inference now uses token matches instead of raw
  substring matches, avoiding `market` -> `mark_index` false positives.

## Boundary

This packet only changes local ZIP CSV archive parsing and descriptor
inference for sandbox diagnostics and sweeps. It does not execute strict
validation, write candidate packs, create paper/live signals, define sizing,
place orders, change runtime mode, write live configuration, mutate source
files, download provider data, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "zip and (market_frame_loader or archive_manifest_builder)"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 7 focused ZIP/archive-loader tests passed.
- 130 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
