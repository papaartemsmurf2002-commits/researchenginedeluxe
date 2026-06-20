# Stage R106 Sandbox Artifact Catalog Integrity Status Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-254-sandbox-artifact-catalog-integrity-status.md`
Status: closed

## Summary

WPR106-254 makes sandbox artifact discovery safer for agent workflows by
surfacing child-artifact integrity health directly in sandbox artifact catalog
rows. Indexed run and suite manifests now show whether their compact child
Parquet/JSON artifacts still match the manifest-recorded SHA-256 and byte-size
metadata.

## Implementation

- Extended `src/tradingbotsuite/research_sandbox/catalog.py`.
- Run manifest rows and suite manifest rows now include:
  `integrity_verification_status`, checked/verified/failed counts,
  mismatched/missing counts, failed artifact keys, and failure reasons.
- The catalog reuses `verify_sandbox_artifact_integrity(...,
  write_report=False)` so catalog indexing does not write verifier reports.
- Non-run/suite artifacts continue to index normally with
  `integrity_verification_status: not_applicable`.
- A tampered `evidence_requests.json` child artifact is now visible as a
  failed integrity row in the catalog.

## Boundary

The packet changes catalog metadata only. It does not execute sandbox sweeps,
execute strict validation, write candidate packs, create live/paper signals,
define sizing, place orders, change runtime mode, write live configuration,
download provider data, mutate source artifacts, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 79 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# first attempt: known local Windows pytest-asyncio WinError 10055 after 460 passed
# rerun: 461 passed
```

## Remaining Work

The artifact catalog now exposes integrity health for run and suite manifests.
Later packets can choose to route global leaderboards or validation-request
bundle exporters through this catalog status before operating on older runs,
but this packet intentionally keeps catalog indexing read-only.
