# Stage R106 Sandbox Artifact Catalog Venue Expansion Gap Worklist Report

Date: 2026-06-19
Packet: `WPR106-356-sandbox-artifact-catalog-venue-expansion-gap-worklist`

## Summary

WPR106-356 adds a catalog-level venue-expansion worklist sidecar for agent
navigation. The sandbox artifact catalog now writes
`sandbox_artifact_catalog_iteration_venue_expansion_gap_worklist.parquet` by
flattening bounded `repair_or_add_venue_expansion_archives` action-plan samples
already present in loaded iteration index JSON payloads.

## Implementation

- Added the new worklist sidecar filename, schema, and first-read sidecar
  navigation metadata.
- Flattened one row per actionable target venue gap with iteration/action
  identity, source queues, path references, target venue, compact market-symbol
  key, data family, interval, target status/action, source coverage metadata,
  compact counts, and non-authorizing flags.
- Added top-level catalog worklist summary fields for row count, source
  artifact/iteration count, target venue counts, target action counts, target
  status counts, and source queue counts.
- Registered the sidecar in the catalog sidecar index with post-write file
  identity and empty-schema Parquet behavior.

## Boundary

The worklist is descriptor navigation metadata only. It does not create archive
descriptors, mutate archive manifests or source files, download provider data,
execute replay commands, run sandbox sweeps, execute or authorize strict
validation, write candidate packs, change archive routing, change replay
readiness, change preflight behavior, change scoring/ranking, change trial IDs,
change evidence-request selection, or claim promotion readiness.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index_summarizes_agent_iterations_and_briefs or artifact_catalog"`:
  3 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`:
  174 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`: 461 passed.
- `git diff --check`: passed with existing LF-to-CRLF warnings only.
- Direct trailing-whitespace scan of packet-touched files: passed.
