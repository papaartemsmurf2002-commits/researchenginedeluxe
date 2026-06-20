# Stage R106 Sandbox Iteration Market Data Cache Report

Date: 2026-06-19
Packet: WPR106-285
Status: closed
Owner: Codex Research Agent

## Summary

WPR106-285 speeds up one-command archive-backed sandbox iterations by passing a
single process-local market-data cache through archive coverage, compatibility
preflight, and the archive sweep. The same resolved local source can now be
read and normalized once across an active iteration instead of once per step.
Source integrity remains descriptor-scoped, and the cache is not serialized
into JSON or Parquet artifacts.

## Implementation

- Added `SandboxMarketDataCache` for normalized market frames and
  source-integrity reads.
- Allowed archive descriptor audit/coverage, compatibility preflight, and
  archive sweep to accept an optional cache.
- Passed one cache through `run_sandbox_agent_iteration` after cached-iteration
  reuse checks and before coverage/preflight/sweep execution.
- Added focused tests for a prewarmed archive sweep cache and one-command
  iteration cross-step source reuse.
- Updated the sandbox research contract and active index.

## Boundary

No candidate pack, paper/live artifact, order or sizing behavior, runtime-mode
change, live configuration write, provider download, strict-cycle execution,
source artifact mutation, validation execution, or promotion claim was added.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "market_data_cache or cache_across_steps or archive_sweep_uses_preloaded or market_frame_loader or readiness_caches"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 15 focused cache tests passed.
- 122 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
