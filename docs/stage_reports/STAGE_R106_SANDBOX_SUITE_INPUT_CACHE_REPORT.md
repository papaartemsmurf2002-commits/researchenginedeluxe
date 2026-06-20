# Stage R106 Sandbox Suite Input Cache Report

Date: 2026-06-19
Packet: `WPR106-287-sandbox-suite-input-cache`
Owner: Codex Research Agent
Status: closed

## Summary

WPR106-287 speeds up archive-backed sandbox suite execution by caching parsed
suite inputs across sequential cases. Repeated references to the same sandbox
run spec, strategy catalog, or venue archive manifest are now parsed once
inside a sequential suite run and reused as descriptor objects for later cases.

Parallel suite execution keeps input caches case-local to avoid shared mutable
state across worker threads. Suite artifacts record only `input_cache_scope`;
cached descriptors are not serialized separately.

## Implementation

- Added a private `_SuiteInputCache` for parsed run specs, strategy catalogs,
  and venue archive descriptors keyed by resolved local path.
- Sequential `run_sandbox_suite` execution now passes one input cache through
  all cases.
- Parallel `run_sandbox_suite` execution creates an isolated input cache per
  case.
- Suite manifests record `input_cache_scope` as either `suite_sequential` or
  `case_local_parallel`.
- Regression coverage proves two sequential suite cases sharing the same
  spec/catalog/archive paths call each loader once.

## Boundary

This packet only changes process-local descriptor parsing reuse inside sandbox
suite execution. It does not execute strict validation, write candidate packs,
create paper/live signals, define sizing, place orders, change runtime mode,
write live configuration, mutate source files, download provider data, or
claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "suite_reuses_input_cache or suite_reuses_market_data_cache or suite_runs_multiple_cases or suite_parallel_execution_preserves_case_order"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 4 focused suite cache tests passed.
- 124 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
