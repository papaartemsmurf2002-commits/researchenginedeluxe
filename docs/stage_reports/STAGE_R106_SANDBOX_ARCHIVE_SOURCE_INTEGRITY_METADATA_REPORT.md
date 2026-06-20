# Stage R106 Sandbox Archive Source Integrity Metadata Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-257-sandbox-archive-source-integrity-metadata.md`
Status: closed

## Summary

WPR106-257 makes sandbox archive manifests more reproducible for agent
workflows by recording local source file SHA-256 and byte-size metadata in
archive build evidence and generated venue descriptors.

## Implementation

- Added optional `source_integrity` metadata to `VenueArchiveDescriptor`.
- Preserved loading of older venue descriptor manifests that omit
  `source_integrity`.
- Archive manifest build rows now include `source_sha256` and
  `source_byte_size` for scanned files.
- Included venue descriptors now carry matching `source_integrity` payloads.
- Archive manifest identity now includes source integrity, so editing a local
  archive file in place changes the generated manifest ID.

## Boundary

The packet changes archive manifest metadata only. It does not execute sandbox
sweeps, execute strict validation, change strategy math, change completed-run
trial IDs, write candidate packs, create paper/live signals, define sizing,
place orders, change runtime mode, write live configuration, download provider
data, mutate source archive files, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "archive_manifest_builder"
# 3 passed, 81 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 84 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# first attempt: known local Windows pytest-asyncio WinError 10055 after 460 passed
# rerun: 461 passed
```

## Remaining Work

Archive manifests now prove local source file identity. Later packets can add a
separate archive-source verifier if agents need a standalone check for a saved
venue archive manifest against current files on disk.
