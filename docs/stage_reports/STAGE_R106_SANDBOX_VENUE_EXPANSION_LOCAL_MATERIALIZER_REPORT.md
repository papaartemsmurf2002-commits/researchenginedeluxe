# Stage R106 Sandbox Venue Expansion Local Materializer Report

Date: 2026-06-20
Packet: `WPR106-366-sandbox-venue-expansion-local-materializer`

## Summary

WPR106-366 adds a descriptor-only local materializer for sandbox
venue-expansion request bundles. It reads
`sandbox_venue_expansion_request_bundle.json`, scans only explicitly supplied
local archive roots, matches local files against requested venue, symbol,
family, interval, and 2024+ window overlap, and writes:

- `sandbox_venue_expansion_descriptor_candidates.json`
- `sandbox_venue_expansion_descriptor_candidates.parquet`
- `sandbox_venue_expansion_manifest_patch_dry_run.json`
- `sandbox_venue_expansion_manifest_patch_dry_run.parquet`

The materializer does not write or modify archive manifests. The patch artifact
is a dry-run report only.

## Changes

- Added `src/tradingbotsuite/research_sandbox/venue_expansion_materializer.py`.
- Exported the materializer and artifact names from
  `tradingbotsuite.research_sandbox`.
- Added the research CLI command
  `materialize-rapid-strategy-sandbox-venue-expansion-requests`.
- Registered the command in `RESEARCH_COMMANDS` and
  `docs/contracts/boundary_contract.md`.
- Documented the dry-run materializer boundary in
  `docs/contracts/sandbox_research_contract.md`.
- Added focused sandbox tests for candidate matching, unmatched-request
  blockers, pre-2024 refusal, no manifest write, and CLI research-root output
  containment.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "venue_expansion_local_materializer or materializes_venue_expansion_requests"`
  - `3 passed, 175 deselected`
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  - `23 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `192 passed`
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `461 passed`
- Ignored local smoke under `outputs/wpr106_366_smoke`
  - `run-rapid-strategy-sandbox-iteration` completed with ranked results,
    descriptor-only strict-validation requests, archive-coverage gaps, and an
    agent brief.
  - After `index-rapid-strategy-sandbox-iterations`,
    `index-rapid-strategy-sandbox-artifacts`, and
    `export-rapid-strategy-sandbox-venue-expansion-requests`, the new
    materializer produced 2 request rows, 1 Bybit descriptor candidate, and 1
    blocked Hyperliquid request.
- `git diff --check`
  - passed with existing LF-to-CRLF warnings only

## Boundary Statement

All outputs remain research-only, observe-only, sandbox-only,
non-promotable, non-candidate-evidence, and ineligible for candidate packs.
The command does not download provider data, mutate source archive files,
write or modify archive manifests, run sandbox sweeps, run strict validation,
write candidate packs, create paper/live signals, define sizing, place
orders, change runtime mode, write live configuration, or claim promotion
readiness.
