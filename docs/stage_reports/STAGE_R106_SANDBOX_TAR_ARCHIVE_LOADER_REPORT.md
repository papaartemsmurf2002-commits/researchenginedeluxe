# Stage R106 Sandbox TAR Archive Loader Report

Date: 2026-06-19
Packet: `WPR106-295-sandbox-tar-archive-loader`
Owner: Codex Research Agent
Status: closed

## Summary

WPR106-295 expands local sandbox archive intake to TAR containers. The sandbox
market-data loader now reads `.tar`, `.tar.gz`, and `.tgz` files containing
CSV, TSV, JSON, JSONL, or NDJSON market-data members without requiring agents
to extract venue drops before archive manifest, audit, preflight, or sweep
loops.

TAR/TGZ member payloads reuse the existing CSV/TSV header detection,
structured JSON parsing, JSONL/NDJSON parsing, venue alias normalization,
source-transformation metadata, and 2024+ filtering paths.

## Implementation

- Added a read-only TAR/TGZ market-data member loader using in-memory member
  payloads.
- Preserved CSV-first member priority semantics for archive containers with
  multiple loadable member types.
- Reused the existing CSV/TSV/JSON/JSONL/NDJSON parser paths so venue aliases,
  Hyperliquid nested `l2Book` flattening, timestamp normalization, and
  midpoint derivation remain consistent across plain files, ZIPs, and TARs.
- Registered `.tar`, `.tar.gz`, and `.tgz` as supported archive manifest
  builder suffixes.
- Added regression coverage for TAR JSONL loading, TAR CSV priority, and
  archive manifest inclusion of TAR JSONL venue exports.

## Boundary

This packet only changes already-local sandbox market-data loading and archive
manifest diagnostics. TAR/TGZ members are not extracted to disk. No provider
download, strict validation execution, candidate-pack write, paper/live signal,
sizing, order placement, runtime-mode change, live configuration write, source
archive mutation, or promotion claim exists.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "tar_jsonl or csv_tar_member"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 3 focused TAR archive-loader tests passed.
- 150 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
