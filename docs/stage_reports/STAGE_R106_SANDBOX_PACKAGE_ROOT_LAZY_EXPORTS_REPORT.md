# Stage R106 Sandbox Package Root Lazy Exports Report

## Summary

WPR106-384 closes the audit M7 package-root coupling gap for the Rapid Strategy
Iteration Sandbox. The sandbox package root still exposes the same public names
through `__all__`, but it no longer eagerly imports catalog, iteration,
market-data, archive, and artifact modules when only
`tradingbotsuite.research_sandbox` is imported.

## Implemented

- Replaced eager root imports in `src/tradingbotsuite/research_sandbox/__init__.py`
  with a static exported-name to owning-module map.
- Added lazy `__getattr__` resolution that imports only the owning module for
  the requested root export and caches the resolved object.
- Added `__dir__` support so the lazy root remains discoverable.
- Added a clean-interpreter regression test proving root import does not import
  `catalog`, accessing `DataWindow` imports `spec` only, and accessing
  `index_sandbox_artifacts` imports `catalog`.

## Why This Path

The audit's broader CLI/operator/web routing concern is still a larger design
topic, but the package-root coupling had a narrow fix. A lazy root preserves
existing package-root imports used by tests and CLI code without requiring
mixed edits to `main.py`, which currently also contains unrelated local
four-bar KNN command work outside this packet.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_post_audit_safety.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -c "import sys; import tradingbotsuite.research_sandbox as sandbox; print(len(sandbox.__all__), 'tradingbotsuite.research_sandbox.catalog' in sys.modules); _ = sandbox.DataWindow; print('tradingbotsuite.research_sandbox.spec' in sys.modules, 'tradingbotsuite.research_sandbox.catalog' in sys.modules)"
python -m compileall -q src\tradingbotsuite
```

Results:

- Focused post-audit safety tests: 18 passed.
- Full sandbox suite: 221 passed.
- Live CLI boundary tests: 26 passed.
- Import smoke printed `109 False` then `True False`, confirming `catalog` is
  not imported by root import or by `DataWindow` access.
- Package compileall passed.

## Boundary Confirmation

This packet changes package import timing only. It does not change sandbox
execution, artifact schemas, trial identity, strict-validation handoff behavior,
candidate-pack gates, live/paper behavior, sizing, order placement, runtime
mode, live configuration, candidate-evidence semantics, or promotion state.
