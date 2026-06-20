# Stage R106 Sandbox Artifact Catalog Replay Bucket Parquet Sidecars Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-322-sandbox-artifact-catalog-replay-bucket-parquet-sidecars.md`

## Summary

WPR106-322 writes compact Parquet sidecars for replay batch-plan bucket queues
and bucket representatives. Agents can now query venue/window-to-plan routing
from flat Parquet rows without loading nested sandbox artifact catalog JSON.

## Outputs

- `sandbox_artifact_catalog_replay_batch_plan_bucket_queue.parquet`
- `sandbox_artifact_catalog_replay_batch_plan_bucket_representatives.parquet`

Both sidecars are written beside `sandbox_artifact_catalog.json` and
`sandbox_artifact_catalog.parquet` when artifact catalog reports are enabled.
Blocked-only or no-bucket catalogs still write empty-schema sidecars for stable
automation.

## Boundary

The sidecars are derived only from already-indexed catalog rows and bounded
replay bucket queues. They retain sandbox boundary flags and expose only
bucket names, counts, artifact path metadata, descriptor-only state, and
explicit non-executing authorization flags. They do not execute replay commands
or validation, download provider data, run strict cycles, mutate strategy
catalogs, mutate archive manifests or source files, write candidate packs,
create paper/live artifacts, define sizing, place orders, change runtime mode,
write live configuration, or make promotion-ready claims.

## Implementation

- Added deterministic sidecar file names and catalog payload paths.
- Flattened archive bucket and archive-window queue items into bucket queue
  Parquet rows.
- Flattened representative artifacts into one row per bucket representative.
- Wrote empty-schema sidecars when no bucket rows exist.
- Added focused tests for non-empty duplicate-ready sidecars and blocked-only
  empty sidecars.
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
