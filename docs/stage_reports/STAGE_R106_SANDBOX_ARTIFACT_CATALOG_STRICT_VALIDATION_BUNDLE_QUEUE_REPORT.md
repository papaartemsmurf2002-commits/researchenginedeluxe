# Stage R106 Sandbox Artifact Catalog Strict Validation Bundle Queue Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-323-sandbox-artifact-catalog-strict-validation-bundle-queue.md`

## Summary

WPR106-323 makes descriptor-only strict-validation request bundles first-class
artifact catalog navigation metadata. Catalog rows now expose bundle IDs,
source scope, execution mode, request counts, deduped descriptor counts, and
duplicate removals. Catalog manifests now include a top-level
strict-validation bundle summary and bounded queue for agent triage.

## Boundary

The strict-validation bundle queue is derived only from already-loaded bundle
payload metadata and catalog rows. It is read-only navigation metadata. It does
not execute or authorize strict validation, execute replay commands, download
provider data, run strict cycles, mutate strategy catalogs, mutate archive
manifests or source files, write candidate packs, create paper/live artifacts,
define sizing, place orders, change runtime mode, write live configuration, or
make promotion-ready claims.

## Implementation

- Projected strict-validation bundle counts into artifact catalog rows:
  `strict_validation_request_count`,
  `strict_validation_deduped_request_count`, and
  `strict_validation_duplicates_removed`.
- Added bundle metadata fields for `bundle_id`, source scope, source directory,
  source manifest path, entrypoint, and descriptor-only execution mode.
- Added `strict_validation_bundle_summary` with artifact, request, deduped,
  duplicate, source-scope, and status counts.
- Added `strict_validation_bundle_queue` with bounded descriptor-only
  path/count metadata and explicit non-authorizing flags.
- Added focused regressions covering run and suite bundles.
- Updated the sandbox research contract and active index.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "artifact_catalog_indexes_known_artifacts"`:
  1 passed, 173 deselected.
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
