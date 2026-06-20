# Stage R106 Sandbox Compatibility Preflight Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-244-sandbox-compatibility-preflight.md`
Status: closed

## Summary

WPR106-244 adds a fast compatibility preflight for Rapid Strategy Iteration
Sandbox runs. Agents can now check strategy/catalog/archive readiness before a
full archive-backed sandbox sweep and see exactly which strategy/venue trial
combinations are runnable or blocked.

## Implementation

- Added `src/tradingbotsuite/research_sandbox/preflight.py` with
  `preflight_sandbox_compatibility()`.
- Added deterministic preflight IDs from the spec, strategy rows, venue
  descriptors, and optional shared market-data path.
- Loaded venue frames through the existing sandbox market loader so pre-2024
  rows are removed before compatibility checks.
- Materialized sandbox blueprint proxy signals after window filtering so
  blueprint-derived strategy rows are not falsely reported as missing signals.
- Reported one row per strategy/venue pair with trial estimates across holding
  periods, exit variants, and filter variants.
- Reported explicit blockers for missing data paths, missing files, loader
  failures, empty 2024+ windows, missing signal/filter columns, and missing
  high/low columns for target/stop exits.
- Wrote `sandbox_compatibility_preflight.json` and
  `sandbox_compatibility_preflight.parquet`.
- Registered `preflight-rapid-strategy-sandbox` as a research command with
  research-root output enforcement and live-boundary coverage.
- Made the sandbox artifact catalog recognize compatibility preflight JSON
  artifacts.

## Boundary

This packet only performs readiness analysis. It does not execute sandbox
sweeps, execute strict validation, write candidate packs, create paper/live
signals, define sizing, place orders, mutate runtime mode, write live
configuration, download provider data, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 67 passed

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
# 19 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

The preflight does not choose strategies, run sweeps, or generate strict
validation specs. It is intended as a cheap agent workflow check before using
the existing sandbox sweep, suite, iteration, and validation-request bundle
commands.
