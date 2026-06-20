# Stage R106 Sandbox Strict Request Source Context Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-259-sandbox-strict-request-source-context.md`
Status: closed

## Summary

WPR106-259 makes sandbox evidence-request descriptors carry compact
source-trial context for faster agent handoff into the existing strict
validation cycle.

## Implementation

- Added `source_trial_context` to sandbox evidence requests.
- The context records source run/trial identity, hypothesis/family/source ID,
  venue, symbol, data family, signal column, side, holding period,
  exit/filter variant IDs, market timestamp bounds, descriptor routing
  metadata, and sandbox execution assumptions.
- Strict-validation request bundle rows preserve the full
  `source_trial_context` and expose convenience fields for venue descriptor
  ID, market start/end, and market-source routing metadata.
- Request IDs remain based on source run ID, source trial ID, and requested
  validation type.

## Boundary

The packet changes sandbox handoff metadata only. It does not execute strict
validation, change strategy math, change trial scoring or ranking, change
trial IDs, write candidate packs, create paper/live signals, define sizing,
place orders, change runtime mode, write live configuration, download provider
data, mutate source archive files, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "archive_sweep_routes_each_venue or validation_request_bundle"
# 3 passed, 83 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 86 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

The strict-validation request descriptors now carry enough source context for
fast handoff triage. Later packets can add a dedicated strict-cycle spec
materializer if a future stage explicitly allows generating historical-cycle
configs from these descriptors; this packet intentionally remains
descriptor-only.
