# Stage R106 Sandbox Compressed Container Members Report

Date: 2026-06-19
Packet: `WPR106-296-sandbox-compressed-container-members`
Owner: Codex Research Agent
Status: closed

## Summary

WPR106-296 expands sandbox ZIP and TAR/TGZ archive-member loading so compressed
members such as `.csv.gz`, `.json.gz`, `.jsonl.gz`, and `.ndjson.gz` are
recognized by compound suffix inside already-local containers. Agents can now
point archive manifest, audit, preflight, and sweep loops at venue drops that
contain compressed member files without manually extracting or decompressing
them first.

## Implementation

- Added shared ZIP/TAR member compound-suffix detection for gzip-compressed
  market-data members.
- Added shared member parsing that decompresses gzip payloads in memory and
  reuses the existing CSV/TSV/JSON/JSONL/NDJSON parser paths.
- Preserved CSV-first priority across plain and compressed member forms.
- Kept Hyperliquid nested `l2Book` flattening, timestamp normalization,
  alias normalization, midpoint derivation, and 2024+ filtering on the same
  normalized path.
- Added focused tests for ZIP `.jsonl.gz` loading, archive manifest inclusion
  from a ZIP `.jsonl.gz` member, and TAR `.csv.gz` priority over JSON members.

## Boundary

This packet only changes already-local sandbox archive member loading and
manifest diagnostics. Members are decompressed in memory and are not extracted
to disk. No provider download, strict validation execution, candidate-pack
write, paper/live signal, sizing, order placement, runtime-mode change, live
configuration write, source archive mutation, or promotion claim exists.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "gzip_jsonl_member or csv_gzip_tar_member"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 3 focused compressed-container member tests passed.
- 153 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
