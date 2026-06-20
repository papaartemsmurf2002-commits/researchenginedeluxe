# Stage R106 Sandbox Iteration Brief Source Summaries Report

Date: 2026-06-19
Packet: `WPR106-302-sandbox-iteration-brief-source-summaries`
Owner: Codex Research Agent
Status: closed

## Summary

WPR106-302 preserves compact source-routing and ZIP/TAR container diagnostics
inside one-command sandbox iteration navigation artifacts. Agents reviewing an
iteration brief, iteration index row, strict-validation action queue, or action
plan can now see the source venue descriptor, routing mode, local source path,
selected container suffix, selected/loadable member counts, bounded member-name
sample, and source market bounds without reopening the strict-validation
request bundle.

## Implementation

- The iteration brief validation-request compactor now includes a bounded
  `source_market_source` summary with descriptor routing fields and container
  diagnostics.
- Each top validation-request item now exposes convenience fields such as
  `source_venue_descriptor_id`, `source_routing_mode`, `source_data_path`,
  `source_container_kind`, `source_selected_member_suffix`,
  `source_selected_member_count`, `source_selected_member_name_sample`, and
  `source_loadable_member_count`.
- Iteration index rows, strict-validation action queue items, and agent
  action-plan items already preserve `top_validation_requests`, so they inherit
  the compact source summaries.
- Added a focused ZIP-backed one-command iteration/index test covering brief,
  index row, action queue, action plan, and Parquet serialization.

## Boundary

This packet only changes agent navigation metadata. It does not change archive
loading, market routing, trial IDs, sweep metrics, ranking math, blocker
semantics, eligibility flags, evidence-request selection, strict validation, or
candidate-pack behavior. Archive members remain read in memory by the existing
loader and are not extracted to disk. No provider download, strict validation
execution, candidate-pack write, paper/live signal, sizing, order placement,
runtime-mode change, live configuration write, source archive mutation, member
extraction, or promotion claim exists.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "agent_iteration_brief_preserves_validation_request_source_summary"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 1 focused ZIP-backed iteration/source-summary test passed.
- 165 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
