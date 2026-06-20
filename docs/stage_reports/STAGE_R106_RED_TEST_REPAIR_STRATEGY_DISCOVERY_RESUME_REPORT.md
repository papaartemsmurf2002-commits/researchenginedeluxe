# Stage R106 Red Test Repair Strategy Discovery Resume Report

Date: 2026-06-20
Packet: `WPR106-363-red-test-repair-strategy-discovery-resume`

## Summary

WPR106-363 repairs the two full-suite blockers called out by the post-audit
roadmap. It keeps the work narrowly scoped to strategy metadata contract
alignment and discovery resume manifest accounting.

## Changes

- Restored the intended 4h `trend_following_v1` spacing search domain by
  removing the stray 4-bar value from the strategy metadata search space.
- Restored the intended 12h `range_reversion_v1` spacing search domain by
  removing the stray 4-bar value from the strategy metadata search space.
- Fixed partial-ledger discovery resume accounting so, when full trial
  hydration is intentionally skipped for large resumes, manifest and snapshot
  counts trust the recovered durable state completed-trial IDs.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\optimization\test_search_space_expansion.py::test_holding_window_search_space_includes_metadata_and_window_defaults -q`
  - `1 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_runner.py::test_discovery_runner_large_zero_stop_resume_recovers_lag_without_full_hydration -q`
  - `1 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\optimization\test_search_space_expansion.py -q`
  - `5 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_runner.py -q`
  - `31 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `189 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  - `23 passed`
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `461 passed`
- `$env:PYTHONPATH='src'; python -m pytest -q -p no:cacheprovider`
  - `1844 passed, 1 skipped, 1 warning`

The full-suite warning is the existing XGBoost mismatched-device warning.

## Boundary Statement

This packet does not change candidate gates, write candidate packs, execute
strict validation, create sandbox evidence authority, create live or paper
signals, add sizing or order-placement logic, change runtime mode, write live
configuration, or create promotion readiness.

