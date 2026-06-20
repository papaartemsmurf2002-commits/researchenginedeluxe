# Stage R106 Sandbox Gzip Archive Loader Report

Date: 2026-06-19
Packet: `WPR106-288-sandbox-gzip-archive-loader`
Owner: Codex Research Agent
Status: closed

## Summary

WPR106-288 expands local archive intake for the research-only rapid strategy
sandbox by supporting gzip-compressed CSV, TSV, JSON, and JSONL market-data
exports. This makes common OKX, Bybit, Hyperliquid, Binance, and local manifest
drop formats loadable without network access or provider downloads.

Archive manifest building now recognizes compound suffixes such as `.csv.gz`
and includes loadable compressed local files instead of skipping them as plain
`.gz` files.

## Implementation

- Added gzip market-frame loader dispatch for `.csv.gz`, `.tsv.gz`,
  `.json.gz`, and `.jsonl.gz`.
- Kept existing 2024+ normalization, venue export alias normalization, and
  descriptor source-integrity behavior.
- Extended archive manifest builder supported suffixes to include the gzip
  compound suffixes.
- Build-report rows now record compound suffixes such as `.csv.gz`.
- Regression coverage proves gzip CSV, gzip JSONL, descriptor source
  integrity against a compressed source file, and archive manifest inclusion of
  a gzipped Bybit-style export.

## Boundary

This packet only changes local archive file parsing for sandbox diagnostics and
sweeps. It does not execute strict validation, write candidate packs, create
paper/live signals, define sizing, place orders, change runtime mode, write
live configuration, mutate source files, download provider data, or claim
promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "gzip or binance_vision_kline_zip or archive_manifest_builder_includes_gzip"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 5 focused gzip/archive-loader tests passed.
- 128 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
