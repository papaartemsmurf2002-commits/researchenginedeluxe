# Stage R106 Sandbox Artifact Integrity Verifier Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-253-sandbox-artifact-integrity-verifier.md`
Status: closed

## Summary

WPR106-253 adds a read-only artifact-integrity verifier for Rapid Strategy
Iteration Sandbox run and suite handoffs. Agents can now verify that compact
Parquet/JSON child artifacts still match the SHA-256 and byte-size metadata in
the run or suite manifest before using those artifacts in later sandbox
analysis.

## Implementation

- Added `src/tradingbotsuite/research_sandbox/integrity.py`.
- Added `verify_sandbox_artifact_integrity()` for run directories, suite
  directories, and manifest paths.
- Verification rows compare expected and actual SHA-256 and byte size for run
  artifacts (`summary.parquet`, `rankings.parquet`, `evidence_requests.json`,
  `evidence_requests.parquet`) and suite artifacts (`suite_index.json`,
  `suite_index.parquet`, `suite_evidence_requests.json`,
  `suite_evidence_requests.parquet`).
- Missing metadata, missing artifact paths, missing files, and hash/size drift
  fail closed in the verification report.
- Added optional JSON/Parquet report writing through
  `artifact_integrity_report.json` and `artifact_integrity_report.parquet`.
- Added the `verify-rapid-strategy-sandbox-artifacts` CLI command with shared
  research-output-root path resolution for `--target` and `--output-dir`.
- Registered the CLI as a research command and documented it in the boundary
  contract.

## Boundary

The verifier is read-only with respect to existing sandbox child artifacts. It
does not execute sandbox sweeps, strict validation, historical cycles, or
candidate gates. It does not write candidate packs, create live/paper signals,
define sizing, place orders, change runtime mode, write live configuration,
download provider data, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 78 passed

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
# 20 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# first attempt: known local Windows pytest-asyncio WinError 10055 after 460 passed
# rerun: 461 passed
```

## Remaining Work

Artifact hash metadata and verification are now first-class sandbox handoff
checks. Later packets can optionally make artifact catalogs surface the latest
verification report status, but that is not needed for correctness of the
current verifier.
