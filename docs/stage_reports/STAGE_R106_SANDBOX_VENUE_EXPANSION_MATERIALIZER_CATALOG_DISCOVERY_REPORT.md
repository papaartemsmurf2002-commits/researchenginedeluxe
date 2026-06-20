# Stage R106 Sandbox Venue Expansion Materializer Catalog Discovery Report

Date: 2026-06-20
Packet: `WPR106-367-sandbox-venue-expansion-materializer-catalog-discovery`

## Summary

WPR106-367 makes WPR106-366 materializer outputs visible through the existing
sandbox artifact catalog. Agents can now run `index_sandbox_artifacts` and
discover both descriptor-candidate artifacts and manifest-patch dry-run
artifacts without opening materializer output folders manually.

## Changes

- Registered `sandbox_venue_expansion_descriptor_candidates.json` as
  `venue_expansion_descriptor_candidates`.
- Registered `sandbox_venue_expansion_manifest_patch_dry_run.json` as
  `venue_expansion_manifest_patch_dry_run`.
- Added catalog row fields for materializer IDs, request counts, descriptor
  candidate counts, dry-run patch row counts, ready/blocked request counts,
  archive scan counts, scan status/reason maps, output paths, and explicit
  false provider/download/archive mutation authorization fields.
- Added a focused regression that materializes a local Bybit descriptor
  candidate, indexes the output directory, and verifies catalog rows preserve
  sandbox boundary flags.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "materializer_catalog"`
  - `1 passed, 178 deselected`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `193 passed`
- `python -m compileall -q src\tradingbotsuite`
  - passed

## Boundary Statement

This packet catalogs existing materializer outputs only. It does not rerun
materialization, download provider data, mutate source archive files, write or
modify archive manifests, execute sandbox sweeps, execute strict validation,
write candidate packs, create paper/live artifacts, define sizing, place
orders, change runtime mode, write live configuration, or claim promotion
readiness.
