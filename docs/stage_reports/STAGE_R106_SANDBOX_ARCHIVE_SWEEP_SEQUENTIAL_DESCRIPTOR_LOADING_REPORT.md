# Stage R106 Sandbox Archive Sweep Sequential Descriptor Loading Report

## Summary

WPR106-385 reduces the audit H9 full-memory pressure in descriptor-routed
sandbox archive sweeps. `run_sandbox_archive_sweep` no longer loads every
descriptor market frame into one dictionary before execution when descriptors
use their own `data_path`; it now loads one descriptor frame, executes that
descriptor's trials, releases the local frame reference, and applies global
ranking once after all descriptor results are collected.

Shared-market-data sweeps still load one shared frame and route it to all
descriptors, which preserves the existing smoke/shared-input behavior.

## Implemented

- Added `apply_rank_top_n` to `run_fixed_hold_sweep_for_venue_frames` so
  callers can defer top-N truncation while preserving the original run spec for
  trial identity.
- Updated descriptor-routed `run_sandbox_archive_sweep` to load descriptor
  frames sequentially and globally rank the combined result set once.
- Preserved preloaded `SandboxMarketDataCache` behavior: cached descriptor
  frames are reused without rereading source data.
- Added a regression test that proves descriptor-routed archive sweeps call the
  per-descriptor loader in descriptor order, never have more than one active
  descriptor load, and match direct multi-frame sweep ranked results.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -k "archive_sweep" -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
python -m compileall -q src\tradingbotsuite
```

Results:

- Archive-sweep focused tests: 4 passed, 196 deselected.
- Full sandbox suite: 222 passed.
- Package compileall passed.

## Boundary Confirmation

This packet changes descriptor-routed archive sweep loading order and deferred
ranking only. It does not change trial identity, artifact schemas,
descriptor-window enforcement, strict-validation behavior, candidate-pack gates,
live/paper behavior, sizing, order placement, runtime mode, live configuration,
candidate-evidence semantics, or promotion state.
