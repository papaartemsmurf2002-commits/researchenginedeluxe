# Stage R106 Sandbox Venue Identity Aliases Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-269-sandbox-venue-identity-aliases.md`
Status: closed

## Summary

WPR106-269 reduces local multi-venue archive setup friction by canonicalizing
common venue identity aliases before sandbox venue descriptor validation.

## Implementation

- Added shared sandbox venue canonicalization in `spec.py`.
- Direct venue archive manifests now accept common labels such as
  `binance_futures`, `okex`, `bybit_usdt_linear`, and `hl_perp`.
- Archive manifest builder `venue` overrides now use the same canonicalization
  path before descriptor inference and validation.
- Existing canonical descriptor values remain unchanged:
  `binance_usdm`, `okx`, `bybit`, `hyperliquid`, and `local_manifest`.
- Unsupported venues still fail closed with a validation error.

## Boundary

This packet only normalizes local sandbox venue descriptor identity. It does
not download provider data, execute sandbox sweeps, execute strict validation,
write candidate artifacts, create paper/live signals, define sizing, place
orders, mutate runtime mode, write live configuration, mutate source archive
files, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "venue_descriptor_loader_canonicalizes_common_venue_aliases or venue_descriptor_rejects_unknown_venue_alias or venue_override_aliases or archive_manifest_builder"
# 10 passed, 94 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 104 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

Additional aliases can be added when real local archive drops expose stable
new venue labels.
