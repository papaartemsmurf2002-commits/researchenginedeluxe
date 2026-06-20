# Stage R106 Sandbox Venue Expansion Candidate Manifest Export Report

Date: 2026-06-20
Packet: `WPR106-368-sandbox-venue-expansion-candidate-manifest-export`

## Summary

WPR106-368 adds an explicit handoff from venue-expansion descriptor candidates
to a new standalone sandbox archive manifest. This closes the manual-copy gap
between WPR106-366 materializer outputs and existing archive coverage,
compatibility preflight, and bounded rerun commands.

## Changes

- Added `export_sandbox_venue_expansion_candidate_manifest`.
- Added report artifacts:
  - `sandbox_venue_expansion_candidate_manifest_report.json`
  - `sandbox_venue_expansion_candidate_manifest_report.parquet`
- Added the research CLI command
  `export-rapid-strategy-sandbox-venue-expansion-candidate-manifest`.
- Registered the command in `RESEARCH_COMMANDS` and the boundary contract.
- Documented the candidate-manifest export boundary in the sandbox research
  contract.
- Added focused tests proving the manifest is loadable, coverage-ready, and
  preflight-compatible, plus CLI output-root containment.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "candidate_manifest"`
  - `2 passed, 179 deselected`
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  - `23 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `195 passed`
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `461 passed`

## Boundary Statement

This packet writes only a new sandbox archive manifest and report under the
requested output directory. It does not mutate source archive files or existing
archive manifests, download provider data, execute sandbox sweeps, execute
strict validation, write candidate packs, create paper/live behavior, define
sizing, place orders, change runtime mode, write live configuration, claim
candidate evidence, or claim promotion readiness.
