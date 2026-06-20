# Stage R106 Sandbox Archive Source Integrity Guard Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-258-sandbox-archive-source-integrity-guard.md`
Status: closed

## Summary

WPR106-258 makes descriptor-routed archive consumers fail closed when a venue
descriptor carries source-file integrity metadata that no longer matches the
current local archive file.

## Implementation

- Added shared descriptor source-integrity validation in
  `src/tradingbotsuite/research_sandbox/market_data.py`.
- Descriptor-routed market-frame loading now raises on source SHA-256 or
  byte-size mismatch before reading the changed file.
- Archive descriptor audit reports source-integrity mismatches as blocker
  reasons.
- Compatibility preflight reports source-integrity mismatches as blocker
  reasons and produces zero runnable trials for that descriptor/strategy row.
- Shared-market-data smoke mode remains available and intentionally bypasses
  descriptor source-integrity checks.

## Boundary

The packet changes local archive source validation only. It does not execute
strict validation, change strategy math, change trial IDs, write candidate
packs, create paper/live signals, define sizing, place orders, change runtime
mode, write live configuration, download provider data, mutate source archive
files, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "source_integrity or descriptor_source"
# 2 passed, 84 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 86 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

Descriptor-routed archive reads now verify source hashes when available. Later
packets can add a dedicated CLI verifier for saved venue archive manifests if
agents need standalone source-file integrity reports without running audit or
preflight.
