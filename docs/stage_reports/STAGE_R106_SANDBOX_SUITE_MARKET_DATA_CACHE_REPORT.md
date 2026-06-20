# Stage R106 Sandbox Suite Market Data Cache Report

Date: 2026-06-19
Packet: `WPR106-286-sandbox-suite-market-data-cache`
Owner: Codex Research Agent
Status: closed

## Summary

WPR106-286 speeds up archive-backed sandbox suite execution by reusing one
process-local `SandboxMarketDataCache` across sequential suite cases. A suite
that runs multiple cases over the same shared local market source now reads and
normalizes that source once across case preflight and archive sweep execution.

Parallel suite execution keeps caches case-local to avoid shared mutable state
across worker threads. Suite artifacts record only `market_data_cache_scope`;
cached frames and source-integrity state are not serialized.

## Implementation

- `run_sandbox_suite` now chooses a suite-level cache for sequential execution
  and isolated per-case caches for parallel execution.
- `_run_suite_case` passes the selected cache through
  `preflight_sandbox_compatibility` and `run_sandbox_archive_sweep`.
- Suite manifests record `market_data_cache_scope` as either
  `suite_sequential` or `case_local_parallel`.
- Regression coverage proves two sequential suite cases sharing one local
  market file read the raw market source once across preflight and sweep.

## Boundary

This packet only changes process-local market-data reuse inside sandbox suite
execution. It does not execute strict validation, write candidate packs,
create paper/live signals, define sizing, place orders, change runtime mode,
write live configuration, mutate source archive files, download provider data,
or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "suite_reuses_market_data_cache or suite_runs_multiple_cases or suite_parallel_execution_preserves_case_order"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 3 focused suite-cache tests passed.
- 123 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
