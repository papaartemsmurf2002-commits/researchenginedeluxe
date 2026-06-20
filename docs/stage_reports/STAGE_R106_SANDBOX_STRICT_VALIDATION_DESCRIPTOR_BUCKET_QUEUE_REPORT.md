# Stage R106 Sandbox Strict Validation Descriptor Bucket Queue Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-326-sandbox-strict-validation-descriptor-bucket-queue.md`

## Summary

WPR106-326 adds a bounded strict-validation descriptor bucket queue to sandbox
artifact catalogs. Agents can now see where descriptor-only validation requests
cluster by venue/symbol and venue/symbol/requested-validation without scanning
every descriptor row.

## Boundary

The bucket queue is derived only from already-flattened strict-validation
descriptor catalog rows. It is read-only navigation metadata. It does not
execute or authorize strict validation, execute replay commands, download
provider data, run strict cycles, mutate strategy catalogs, mutate archive
manifests or source files, write candidate packs, create paper/live artifacts,
define sizing, place orders, change runtime mode, write live configuration, or
make promotion-ready claims.

## Implementation

- Added bounded descriptor bucket queues grouped by `venue|symbol` and
  `venue|symbol|requested_validation`.
- Added descriptor, bundle, source-trial, top-score, and representative
  descriptor/source-trial/bundle ID counts.
- Added
  `sandbox_artifact_catalog_strict_validation_descriptor_bucket_queue.parquet`
  with stable empty-schema behavior.
- Added catalog payload metadata for queue limits, queue count, queue rows,
  sidecar path, and sidecar row count.
- Added focused regressions covering populated multi-venue bucket rows and
  empty no-bundle sidecars.
- Updated the sandbox research contract and active index.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "artifact_catalog"`:
  2 passed, 172 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`:
  174 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`:
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q`:
  11 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`:
  461 passed.
