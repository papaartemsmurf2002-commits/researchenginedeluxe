# Stage R106 - Sandbox Venue Expansion Request Bundle

## Packet

WPR106-357 - Sandbox Venue Expansion Request Bundle

## Summary

Implemented a descriptor-only venue-expansion request bundle for the rapid
strategy sandbox. The exporter reads an existing `sandbox_artifact_catalog.json`
and its `sandbox_artifact_catalog_iteration_venue_expansion_gap_worklist.parquet`
sidecar, dedupes actionable OKX, Bybit, and Hyperliquid archive repair/add
targets, and writes:

- `sandbox_venue_expansion_request_bundle.json`
- `sandbox_venue_expansion_request_bundle.parquet`

Each descriptor keeps target venue, compact market-symbol key, data family,
interval, target action/status, source queues, source iteration/run IDs, source
artifact paths, bounded source references, coverage counts, blocker counts, and
explicit non-authorization flags.

## Boundary

The bundle is research-only, sandbox-only, descriptor-only, observe-only, and
non-promotable. It does not download provider data, create archive descriptors,
mutate archive manifests, mutate source files, execute replay commands, execute
strict validation, write candidate packs, create paper/live artifacts, place
orders, define sizing, change runtime mode, write live configuration, change
trial IDs, change scoring/ranking, change evidence-request selection, or claim
promotion readiness.

The exporter rejects pre-2024 requested or observed market windows in worklist
rows and records `pre_2024_data_allowed: false`.

## Implementation

- Added `tradingbotsuite.research_sandbox.venue_expansion_requests`.
- Exported the new function and artifact constants from
  `tradingbotsuite.research_sandbox`.
- Registered `sandbox_venue_expansion_request_bundle.json` in sandbox artifact
  catalog discovery as `venue_expansion_request_bundle`.
- Added the research CLI command
  `export-rapid-strategy-sandbox-venue-expansion-requests`.
- Registered the command in `RESEARCH_COMMANDS` and boundary docs.
- Added sandbox payload/catalog tests and live CLI boundary path-guard tests.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "venue_expansion_request or iteration_index_summarizes_agent_iterations_and_briefs"`:
  2 passed, 173 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`:
  23 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`:
  175 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`: 461 passed.
- `git diff --check`: passed with existing LF-to-CRLF warnings only.
- Targeted trailing-whitespace scan of packet-touched files: no findings.
