# Stage R106 Sandbox Readiness Source Cache Report

Date: 2026-06-19
Packet: WPR106-284
Status: closed
Owner: Codex Research Agent

## Summary

WPR106-284 speeds up the mandatory archive-backed readiness path before sandbox
sweeps. Archive audit/coverage now reuses loaded and normalized market frames
for repeated descriptor source paths inside one audit. Compatibility preflight
now reuses loaded, spec-windowed, and strategy-materialized frames for repeated
descriptor source paths inside one preflight run. Source integrity remains
descriptor-scoped and is evaluated before cached market data is used.

## Implementation

- Added `descriptor_source_integrity_errors_with_cache` and
  `normalized_market_data_source_key` in the sandbox market-data module.
- Updated archive descriptor audit to cache normalized market frames by
  resolved source path.
- Updated compatibility preflight to cache prepared source frames by resolved
  source path after integrity checks pass.
- Added focused regressions for same-source audit/preflight reuse and
  integrity-before-cache behavior.
- Updated the sandbox research contract and active index.

## Boundary

No candidate pack, paper/live artifact, order or sizing behavior, runtime-mode
change, live configuration write, provider download, strict-cycle execution,
source artifact mutation, validation execution, or promotion claim was added.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "readiness_caches or reuse_identical_descriptor_sources or market_frame_loader"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "archive_descriptor_audit or archive_audit_and_preflight or readiness_caches or preflight_reuses or cli_command_preflights"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 14 focused cache tests passed.
- 8 archive/preflight-focused tests passed.
- 120 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
