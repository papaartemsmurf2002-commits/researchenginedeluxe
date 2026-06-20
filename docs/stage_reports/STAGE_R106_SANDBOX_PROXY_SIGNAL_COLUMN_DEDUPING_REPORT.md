# Stage R106 Sandbox Proxy Signal Column Deduping Report

## Summary

WPR106-387 reduces the audit H9 proxy-signal memory pressure in high-throughput
sandbox execution and compatibility preflight. Identical blueprint proxy signal
definitions now materialize into one canonical market-frame column, while each
strategy row keeps its original descriptor-facing `signal_column`.

The alias is stored in DataFrame attrs and resolved only inside sandbox
preparation, signal-mask construction, and preflight blocker checks. Direct
manual/precomputed signal columns keep the existing behavior.

## Implemented

- Added deterministic blueprint signal cache keys from blueprint id, blueprint
  version, signal kind, side, and signal-affecting parameters.
- Added canonical materialized proxy signal columns plus
  `sandbox_signal_column_aliases` frame metadata.
- Updated fast sandbox sweeps to materialize duplicate blueprint signals once
  and use the blueprint signal definition for signal-mask cache reuse.
- Updated compatibility preflight to resolve deduped signal aliases before
  active-signal counts and missing-signal blocker checks.
- Added focused regressions for alias metadata, sweep execution, and preflight
  with duplicate proxy strategy rows.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -k "blueprint or signal_mask or preflight" -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest -q
```

Results:

- Focused blueprint/signal/preflight slice: 18 passed, 186 deselected.
- Full sandbox suite: 226 passed.
- Package compileall passed.
- Contracts: 462 passed.
- Live CLI boundary: 26 passed.
- Full suite: 1896 passed, 1 skipped, 1 XGBoost device warning.

## Boundary Confirmation

This packet changes only in-memory blueprint proxy signal materialization and
mask-cache reuse. It preserves strategy descriptors, original `signal_column`
values, trial identity inputs, ranking semantics, artifact schemas,
descriptor-window enforcement, proxy-only labeling, strict-validation behavior,
candidate-pack gates, live/paper behavior, sizing, order placement, runtime
mode, live configuration, candidate-evidence semantics, and promotion state.
