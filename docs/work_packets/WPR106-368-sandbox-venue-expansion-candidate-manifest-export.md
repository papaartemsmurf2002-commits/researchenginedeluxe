# WPR106-368 - Sandbox Venue Expansion Candidate Manifest Export

## Status

closed

## Objective

Convert WPR106-366 descriptor candidates into a new standalone sandbox
`venue_archives.json` manifest under a configured output directory so agents
can run archive coverage, preflight, or bounded sandbox reruns without manually
copying descriptor payloads.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-366-sandbox-venue-expansion-local-materializer.md`
- `docs/work_packets/WPR106-367-sandbox-venue-expansion-materializer-catalog-discovery.md`

## Allowed paths

- `src/tradingbotsuite/research_sandbox/venue_expansion_materializer.py`
- `src/tradingbotsuite/research_sandbox/__init__.py`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/command_registry.py`
- `tests/research_sandbox/**`
- `tests/live/test_cli_boundary.py`
- `docs/contracts/sandbox_research_contract.md`
- `docs/contracts/boundary_contract.md`
- `docs/work_packets/WPR106-368-sandbox-venue-expansion-candidate-manifest-export.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_VENUE_EXPANSION_CANDIDATE_MANIFEST_EXPORT_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered

## Boundary constraints

- Write only a new sandbox archive manifest and report under the requested
  output directory.
- Do not mutate source archive files or existing archive manifests.
- Do not download provider data.
- Do not run sandbox sweeps, strict validation, replay commands, paper/live
  flows, order placement, sizing, runtime-mode changes, live config writes, or
  candidate-pack writes.
- Preserve sandbox boundary flags and 2024+ descriptor windows.

## Acceptance criteria

- Reads only WPR106-366 descriptor-candidate JSON artifacts.
- Fails closed if descriptor candidates are missing, malformed, pre-2024, or
  violate sandbox boundaries.
- Writes a deterministic subdirectory containing `venue_archives.json`,
  `sandbox_venue_expansion_candidate_manifest_report.json`, and a Parquet
  report.
- The written manifest is loadable by `load_venue_archive_descriptors`.
- CLI input/output paths stay under the configured research output root.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "candidate_manifest_export"
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Exit evidence

- Added `export_sandbox_venue_expansion_candidate_manifest`, which reads
  WPR106-366 descriptor-candidate JSON and writes a new standalone sandbox
  `venue_archives.json` manifest under a deterministic manifest ID directory.
- Added report outputs:
  `sandbox_venue_expansion_candidate_manifest_report.json` and
  `sandbox_venue_expansion_candidate_manifest_report.parquet`.
- Added the research CLI command
  `export-rapid-strategy-sandbox-venue-expansion-candidate-manifest` with
  descriptor-candidate input and output path guarding under the configured
  research output root.
- The written manifest is loadable by `load_venue_archive_descriptors` and was
  exercised through archive coverage and compatibility preflight in focused
  tests.
- Validation passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "candidate_manifest"`
  reported 2 passed / 179 deselected;
  `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  reported 23 passed;
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  reported 195 passed;
  `python -m compileall -q src\tradingbotsuite` passed;
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` reported
  461 passed.
