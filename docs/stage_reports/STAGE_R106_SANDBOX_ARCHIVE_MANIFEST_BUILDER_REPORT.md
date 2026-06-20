# Stage R106 Sandbox Archive Manifest Builder Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-239-sandbox-archive-manifest-builder.md`
Status: closed

## Summary

WPR106-239 adds a local archive manifest builder for the Rapid Strategy
Iteration Sandbox. Agents can now point at local archive roots and produce a
loadable `venue_archives.json` manifest plus a compact build report before
auditing or sweeping the data.

## Implementation

- Added `src/tradingbotsuite/research_sandbox/archive_manifest.py`.
- Added `build_sandbox_archive_manifest`.
- Supported local archive inputs are CSV, TSV, JSON, JSONL, Parquet, and simple
  Binance Vision kline ZIP files.
- The builder reuses the sandbox market-frame loader, so pre-2024 rows are
  filtered out before descriptor windows, row counts, or bounds are written.
- Venue, symbol, data family, and interval are inferred from local path/file
  names, with CLI overrides available for raw vendor drops.
- Unsupported files, loader failures, no-2024+ files, and files without enough
  descriptor identity are skipped with explicit reasons.
- Output writes:
  - `venue_archives.json`;
  - `archive_manifest_build_report.json`;
  - `archive_manifest_build_report.parquet`.
- Repeated builds with the same roots and overrides refresh the same
  deterministic manifest directory.
- Added `build-rapid-strategy-sandbox-archive-manifest` as a research CLI
  command with research-root `--output-dir` enforcement.
- Registered the command in the research command registry and boundary
  contract.
- Extended the sandbox research contract with archive manifest builder rules.
- Extended the sandbox artifact catalog to discover generated archive manifests
  and build reports.

## Boundary

Archive manifest builds are local sandbox diagnostics. They carry:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `sandbox_only: true`
- `candidate_evidence: false`
- `candidate_pack_eligible: false`

They do not download provider data, execute strategy sweeps, execute strict
validation, write candidate packs, create paper/live signals, define sizing,
place orders, mutate runtime mode, write live configuration, or claim promotion
readiness.

## Validation

Focused validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
# 52 passed

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
# 15 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed
```

Contract baseline attempt:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 460 passed, 1 pytest-asyncio setup error, 1 warning
```

The baseline failure occurred before the affected async contract test body ran:
Windows failed to create the event-loop `socket.socketpair()` with
`WinError 10055`. A targeted rerun of the same async contract test and an
explicit selector-policy rerun failed the same way. `ISSUE-R106-026` records
this local validation-environment blocker.

## Remaining Work

This packet does not add provider downloads, UI inspection, sandbox sweep
execution, strict validation execution, candidate-pack generation, or a fix for
the local Windows socket exhaustion condition. Those remain separate follow-up
work under the active sandbox objective and known-issues process.
