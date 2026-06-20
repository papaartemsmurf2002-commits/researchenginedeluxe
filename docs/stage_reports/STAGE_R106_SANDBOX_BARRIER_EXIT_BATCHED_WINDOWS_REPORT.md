# Stage R106 Sandbox Barrier Exit Batched Windows Report

## Summary

WPR106-386 reduces the audit H9 dense-window memory pressure in sandbox
target/stop exit sweeps. `_barrier_exit_prices()` now splits eligible entries
into bounded batches before building the primary-bar entry-by-hold target/stop
window matrices.

The existing vectorized barrier semantics are preserved inside each batch:
target-only, stop-only, and conservative target/stop exits still use the same
primary-bar high/low proxy, stop-first same-bar policy, and fixed-hold close
fallback when no barrier touches.

## Implemented

- Added a bounded entry-batch size for sandbox barrier exits.
- Extracted the original vectorized target/stop matrix logic into a per-batch
  helper.
- Added a regression test that forces a tiny batch size and compares the
  multi-batch output against the single-batch vector path for long and short
  target-only, stop-only, and conservative target/stop variants.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -k "barrier" -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
python -m compileall -q src\tradingbotsuite
```

Results:

- Barrier focused tests: 3 passed, 198 deselected.
- Full sandbox suite: 223 passed.
- Package compileall passed.

## Boundary Confirmation

This packet changes only barrier-exit temporary allocation shape. It does not
change trial identity, ranking semantics, artifact schemas, descriptor-window
enforcement, strategy signals, fill assumptions, strict-validation behavior,
candidate-pack gates, live/paper behavior, sizing, order placement, runtime
mode, live configuration, candidate-evidence semantics, or promotion state.
