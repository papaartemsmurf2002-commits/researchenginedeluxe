# Stage R106 Sandbox Archive Descriptor Audit Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-238-sandbox-archive-descriptor-audit.md`
Status: closed

## Summary

WPR106-238 adds a fast readiness audit for Rapid Strategy Iteration Sandbox
venue archive manifests. Agents can now check local descriptor routing, 2024+
market coverage, descriptor-window row coverage, and OHLC availability before
launching larger sandbox sweeps.

## Implementation

- Added `src/tradingbotsuite/research_sandbox/archive_audit.py`.
- Added `audit_sandbox_archive_descriptors`.
- The audit reuses existing venue descriptor and market-frame loaders.
- Descriptor-local `data_path` routing is supported, including manifest-relative
  paths.
- Optional shared `--market-data` routing remains available for smoke audits.
- Audit rows include descriptor ID, venue, symbol, data family, interval,
  routing mode, source path, manifest path, source access mode, checksum policy,
  normalized 2024+ row count, descriptor-window row count, timestamp bounds,
  columns, OHLC availability, status, blocker reasons, and warning reasons.
- Missing data paths, missing files, loader failures, empty normalized 2024+
  frames, and empty descriptor windows are reported as blockers.
- Missing `high` or `low` columns are reported as warnings so agents can
  distinguish fixed-hold-ready data from target/stop-ready data.
- Audit output writes `archive_descriptor_audit.json` and
  `archive_descriptor_audit.parquet` under a deterministic audit directory.
- Repeated audits with the same manifest and shared market path refresh the same
  deterministic audit artifact, supporting agent preflight loops.
- Added `audit-rapid-strategy-sandbox-archives` as a research CLI command with
  research-root `--output-dir` enforcement.
- Registered the command in the research command registry and boundary
  contract.
- Extended the sandbox research contract with archive descriptor audit rules.

## Boundary

Archive descriptor audits are sandbox readiness diagnostics. They carry:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `sandbox_only: true`
- `candidate_evidence: false`
- `candidate_pack_eligible: false`

They do not execute strategy sweeps, execute strict validation, write candidate
packs, create paper/live signals, define sizing, place orders, mutate runtime
mode, write live configuration, or claim promotion readiness.

## Validation

Final validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
# 49 passed

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
# 14 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

This packet does not add provider download orchestration, UI inspection, sandbox
sweep execution, strict validation execution, or candidate-pack generation.
Those remain separate follow-up work under the active sandbox objective.
