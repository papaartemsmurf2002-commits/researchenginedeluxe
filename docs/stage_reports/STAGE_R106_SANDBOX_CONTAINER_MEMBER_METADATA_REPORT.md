# Stage R106 Sandbox Container Member Metadata Report

Date: 2026-06-19
Packet: `WPR106-298-sandbox-container-member-metadata`
Owner: Codex Research Agent
Status: closed

## Summary

WPR106-298 adds bounded member-selection metadata for ZIP and TAR/TGZ sandbox
market-data containers. The sandbox still selects one highest-priority loadable
member suffix and loads only members of that selected suffix, but the selected
container details now remain visible after 2024+ normalization and in archive
manifest build reports.

This removes an agent-workflow blind spot after WPR106-297: chunked venue drops
could load correctly, but reports did not show which member class/count was
used.

## Implementation

- ZIP and TAR/TGZ loaders attach `sandbox_container_member_metadata` to raw
  loaded frames before normalization.
- Normalization metadata now includes `container_member_metadata` and
  `container_member_count`.
- Archive manifest build rows expose nested `container_member_metadata` plus
  searchable summary fields: `container_kind`, `selected_member_suffix`,
  `selected_member_count`, `selected_member_name_sample`,
  `selected_member_names_truncated`, `available_member_suffix_counts`,
  `available_member_suffix_count`, and `loadable_member_count`.
- Member-name samples are bounded and deterministic.
- Added focused tests for ZIP metadata, TAR metadata, and archive manifest
  JSON/Parquet member-metadata rows.

## Boundary

This packet only changes already-local sandbox archive metadata and manifest
diagnostics. Archive members are read in memory and are not extracted to disk.
No provider download, strict validation execution, candidate-pack write,
paper/live signal, sizing, order placement, runtime-mode change, live
configuration write, source archive mutation, member extraction, or promotion
claim exists.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "container_member_metadata"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 3 focused container member-metadata tests passed.
- 160 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
