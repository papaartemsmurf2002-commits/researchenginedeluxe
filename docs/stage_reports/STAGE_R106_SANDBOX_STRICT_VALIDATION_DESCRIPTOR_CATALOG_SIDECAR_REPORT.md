# Stage R106 Sandbox Strict Validation Descriptor Catalog Sidecar Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-325-sandbox-strict-validation-descriptor-catalog-sidecar.md`

## Summary

WPR106-325 writes a cross-bundle strict-validation descriptor Parquet sidecar
from sandbox artifact catalogs. Agents can now query individual descriptor-only
validation requests across run and suite bundles from one flat sidecar without
opening each bundle JSON or bundle Parquet.

## Boundary

The descriptor sidecar is derived only from already-loaded strict-validation
bundle JSON payloads that pass sandbox boundary validation. It is read-only
navigation metadata. It does not execute or authorize strict validation,
execute replay commands, download provider data, run strict cycles, mutate
strategy catalogs, mutate archive manifests or source files, write candidate
packs, create paper/live artifacts, define sizing, place orders, change runtime
mode, write live configuration, or make promotion-ready claims.

## Implementation

- Added
  `sandbox_artifact_catalog_strict_validation_descriptors.parquet` beside the
  existing artifact catalog outputs.
- Flattened strict-validation bundle descriptor rows into catalog-level Parquet
  rows with descriptor identity, source trial identity, source scope, venue,
  symbol, market-window, source routing, compact source metrics,
  required-evidence count, entrypoint, execution mode, and explicit
  non-authorizing flags.
- Added a stable empty-schema sidecar column set for catalogs with no
  descriptor rows.
- Added catalog payload metadata for descriptor sidecar path, row count, and
  compact descriptor summary rollups.
- Added focused regressions covering run/suite descriptors, multi-venue
  descriptor coverage, and empty no-bundle sidecar behavior.
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
