# Stage R106 Sandbox Archive Container Audit Coverage Report

Date: 2026-06-19
Packet: `WPR106-299-sandbox-archive-container-audit-coverage`
Owner: Codex Research Agent
Status: closed

## Summary

WPR106-299 propagates ZIP/TAR container member-selection diagnostics from
normalized sandbox market frames into archive descriptor audits and archive
coverage matrices. Agents can now inspect selected member suffixes, member
counts, available suffix counts, and bounded member-name samples from the
preflight-oriented audit/coverage artifacts without reopening manifest build
reports.

## Implementation

- Archive descriptor audit rows now include `container_member_metadata`,
  `container_kind`, `selected_member_suffix`, `selected_member_count`,
  `selected_member_name_sample`, `selected_member_names_truncated`,
  `available_member_suffix_counts`, `available_member_suffix_count`, and
  `loadable_member_count`.
- Archive coverage rows now aggregate container diagnostics into
  `container_kinds`, `selected_member_suffixes`,
  `container_descriptor_count`, `ready_container_descriptor_count`,
  `selected_member_count`, `ready_selected_member_count`,
  `loadable_member_count`, `selected_member_suffix_counts`,
  `available_member_suffix_counts`, and `selected_member_name_sample`.
- Non-container sources and blocked descriptors keep empty/zero defaults.
- Existing readiness blockers, row counts, source-integrity checks, requested
  window behavior, and coverage bucket identity are unchanged.
- Added focused tests for audit JSON/Parquet propagation and coverage
  JSON/Parquet aggregation.

## Boundary

This packet only changes already-local sandbox archive diagnostics. It does
not change archive loading, sweep metrics, trial identity, evidence requests,
or strict validation behavior. Archive members are read in memory by the
existing loader and are not extracted to disk. No provider download, strict
validation execution, candidate-pack write, paper/live signal, sizing, order
placement, runtime-mode change, live configuration write, source archive
mutation, member extraction, or promotion claim exists.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "archive_descriptor_audit_records_container_member_metadata or archive_coverage_matrix_aggregates_container_member_metadata"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 2 focused archive container audit/coverage tests passed.
- 162 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
