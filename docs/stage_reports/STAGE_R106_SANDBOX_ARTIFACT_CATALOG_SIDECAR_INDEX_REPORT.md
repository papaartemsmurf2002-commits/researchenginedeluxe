# Stage R106 Sandbox Artifact Catalog Sidecar Index Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-329-sandbox-artifact-catalog-sidecar-index.md`

## Summary

WPR106-329 adds a compact sandbox artifact catalog sidecar index Parquet file.
Agents can now discover catalog, replay batch-plan, and strict-validation
sidecar categories, names, roles, paths, row counts, and empty status without
parsing the full catalog JSON first.

## Boundary

The sidecar index is derived only from catalog writer outputs and already
computed row counts. It is read-only navigation metadata. It does not execute
or authorize strict validation, execute replay commands, download provider
data, run strict cycles, mutate strategy catalogs, mutate archive manifests or
source files, write candidate packs, create paper/live artifacts, define
sizing, place orders, change runtime mode, write live configuration, or make
promotion-ready claims.

## Implementation

- Added fixed `sandbox_artifact_catalog_sidecar_index.parquet` output.
- Added stable sidecar index schema and rows for catalog, replay batch-plan, and
  strict-validation Parquet sidecars.
- Added catalog payload metadata for sidecar index path, row count, and rows.
- Added focused regressions covering populated sidecar indexes and
  failed-integrity empty strict-validation sidecars.
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
