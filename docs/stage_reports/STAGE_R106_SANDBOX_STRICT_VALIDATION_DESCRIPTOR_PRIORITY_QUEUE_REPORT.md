# Stage R106 Sandbox Strict Validation Descriptor Priority Queue Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-328-sandbox-strict-validation-descriptor-priority-queue.md`

## Summary

WPR106-328 adds a bounded strict-validation descriptor priority queue and
Parquet sidecar to sandbox artifact catalogs. Agents can now start from the
highest-priority descriptor-only evidence requests across bundles without
scanning the full descriptor sidecar first.

## Boundary

The priority queue is derived only from already-flattened strict-validation
descriptor catalog rows. It is read-only navigation metadata. It does not
execute or authorize strict validation, execute replay commands, download
provider data, run strict cycles, mutate strategy catalogs, mutate archive
manifests or source files, write candidate packs, create paper/live artifacts,
define sizing, place orders, change runtime mode, write live configuration, or
make promotion-ready claims.

## Implementation

- Added a bounded descriptor priority queue sorted by source metric score,
  source metric rank, and stable descriptor identity.
- Added
  `sandbox_artifact_catalog_strict_validation_descriptor_queue.parquet` with
  stable empty-schema behavior.
- Added catalog payload metadata for queue limit, queue count, queue rows,
  sidecar path, and sidecar row count.
- Added focused regressions covering populated priority rows and empty
  failed-integrity sidecars.
- Updated the sandbox research contract, active index, and orchestrator ledger.

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
