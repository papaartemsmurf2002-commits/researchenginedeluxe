# Stage R106 Sandbox Preflight Container Metadata Report

Date: 2026-06-19
Packet: `WPR106-300-sandbox-preflight-container-metadata`
Owner: Codex Research Agent
Status: closed

## Summary

WPR106-300 exposes ZIP/TAR container member-selection diagnostics as
first-class compatibility preflight row fields. Agents no longer need to parse
the nested `normalization` JSON blob to see which container member suffix was
selected, how many members were loaded, and which other loadable member suffixes
were present when evaluating runnable and blocked trial estimates.

## Implementation

- Compatibility preflight rows now include `container_member_metadata`,
  `container_kind`, `selected_member_suffix`, `selected_member_count`,
  `selected_member_name_sample`, `selected_member_names_truncated`,
  `available_member_suffix_counts`, `available_member_suffix_count`, and
  `loadable_member_count`.
- The fields are extracted from existing normalization metadata only; loading,
  windowing, materialized signals, trial estimates, blockers, and evidence
  requests are unchanged.
- Non-container sources keep empty/zero defaults.
- Added a focused JSON/Parquet test for a runnable ZIP-backed preflight row.

## Boundary

This packet only changes compatibility preflight diagnostics. It does not
change archive loading, sweep metrics, trial identity, evidence requests, or
strict validation behavior. Archive members are read in memory by the existing
loader and are not extracted to disk. No provider download, strict validation
execution, candidate-pack write, paper/live signal, sizing, order placement,
runtime-mode change, live configuration write, source archive mutation, member
extraction, or promotion claim exists.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "preflight_records_container_member_metadata"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 1 focused preflight container-metadata test passed.
- 163 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
