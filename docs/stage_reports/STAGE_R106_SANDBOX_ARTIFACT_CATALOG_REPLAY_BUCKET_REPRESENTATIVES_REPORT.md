# Stage R106 Sandbox Artifact Catalog Replay Bucket Representatives Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-321-sandbox-artifact-catalog-replay-bucket-representatives.md`

## Summary

WPR106-321 adds bounded archive bucket and archive-window bucket representative
queues to sandbox artifact catalogs. Agents can now jump from a venue/window
bucket to representative descriptor-only replay batch-plan artifacts without
scanning every replay queue item or opening every batch-plan JSON.

## Boundary

The representative queues are derived only from already-indexed catalog rows.
They expose bucket names, ready/planned bucket counts, bounded artifact path
metadata, descriptor-only state, and explicit non-executing authorization flags
for agent triage. They do not execute replay commands or validation, download
provider data, run strict cycles, mutate strategy catalogs, mutate archive
manifests or source files, write candidate packs, create paper/live artifacts,
define sizing, place orders, change runtime mode, write live configuration, or
make promotion-ready claims.

## Implementation

- Added a bounded archive bucket representative queue to the artifact catalog
  payload.
- Added a bounded archive-window bucket representative queue to the artifact
  catalog payload.
- Added per-bucket representative artifact metadata with ready/planned bucket
  counts and descriptor-only boundary flags.
- Kept blocked-only replay batch plans out of bucket queues when they have no
  ready/planned archive bucket maps.
- Added focused regressions for duplicate-rich ready plans and blocked-only
  plans.
- Updated the sandbox research contract and active index.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "input_replay"`:
  3 passed, 171 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "input_replay or iteration_index"`:
  7 passed, 167 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`:
  174 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`:
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q`:
  11 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`:
  461 passed.
