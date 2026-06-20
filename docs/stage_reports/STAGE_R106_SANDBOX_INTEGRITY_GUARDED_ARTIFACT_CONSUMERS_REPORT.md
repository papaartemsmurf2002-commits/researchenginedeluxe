# Stage R106 Sandbox Integrity-Guarded Artifact Consumers Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-255-sandbox-integrity-guarded-artifact-consumers.md`
Status: closed

## Summary

WPR106-255 makes direct sandbox artifact consumers fail closed on stale or
tampered run/suite child artifacts. Consumers now verify manifest-recorded
SHA-256 and byte-size metadata before opening compact Parquet/JSON source
files.

## Implementation

- Added `require_sandbox_artifact_integrity()` as a no-report guard around the
  existing sandbox artifact verifier.
- Guarded run analysis before reading rankings or evidence requests.
- Guarded run and suite hypothesis falsification before reading run/suite child
  artifacts.
- Guarded global leaderboard aggregation before reading each source run's
  rankings/evidence files.
- Guarded run and suite strict-validation request bundle export before reading
  evidence-request descriptor files.
- Added tamper regressions for run and suite child artifacts.

## Boundary

The packet changes read-time verification only. It does not execute sandbox
sweeps, execute strict validation, change strategy math, write candidate packs,
create paper/live signals, define sizing, place orders, change runtime mode,
write live configuration, download provider data, mutate source artifacts, or
claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 81 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# first attempt: known local Windows pytest-asyncio WinError 10055 after 460 passed
# rerun: 461 passed
```

## Remaining Work

This closes the immediate stale-artifact trust gap for direct run/suite
consumers. Later packets can extend the same pattern to any new sandbox
artifact reader added after WPR106-255.
