# Stage R106 Sandbox Strict Validation Bundle Parquet Sidecar Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-324-sandbox-strict-validation-bundle-parquet-sidecar.md`

## Summary

WPR106-324 writes a compact Parquet sidecar for sandbox artifact catalog
strict-validation bundle queues. Agents can now query descriptor-only
strict-validation handoff bundles from flat rows without opening the full
catalog JSON or every bundle JSON. Catalogs with no bundle queue still write an
empty-schema sidecar for stable automation.

## Boundary

The sidecar is derived only from the bounded catalog queue that WPR106-323
introduced. It is read-only navigation metadata. It does not execute or
authorize strict validation, execute replay commands, download provider data,
run strict cycles, mutate strategy catalogs, mutate archive manifests or source
files, write candidate packs, create paper/live artifacts, define sizing, place
orders, change runtime mode, write live configuration, or make promotion-ready
claims.

## Implementation

- Added
  `sandbox_artifact_catalog_strict_validation_bundle_queue.parquet` beside the
  existing catalog JSON/Parquet outputs.
- Added a stable empty-schema sidecar column set for no-bundle catalogs.
- Flattened strict-validation bundle queue rows into Parquet rows carrying
  queue rank, status, source scope, bundle path, entrypoint, execution mode,
  request counts, descriptor counts, and explicit non-authorizing flags.
- Added catalog payload metadata for sidecar path and row count.
- Added focused regressions for populated run/suite bundle sidecar rows and
  empty no-bundle sidecar behavior.
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
