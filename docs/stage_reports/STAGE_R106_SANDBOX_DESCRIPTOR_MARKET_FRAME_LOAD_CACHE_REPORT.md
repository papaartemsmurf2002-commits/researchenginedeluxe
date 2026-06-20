# Stage R106 Sandbox Descriptor Market Frame Load Cache Report

Date: 2026-06-19
Packet: WPR106-283
Status: closed
Owner: Codex Research Agent

## Summary

WPR106-283 speeds up descriptor-routed sandbox setup by caching loaded and
normalized market frames for identical resolved descriptor `data_path` values
inside one batch. The loader still verifies every descriptor's
`source_integrity` metadata before returning a cached frame for that
descriptor, still filters pre-2024 rows during normalization, and still keeps
distinct resolved source paths as distinct frame objects.

## Implementation

- Added resolved-path cache keys for descriptor batch market-frame loading.
- Added a batch-local file-integrity cache so identical source files are not
  re-hashed repeatedly during one descriptor batch.
- Preserved shared-market-data smoke behavior.
- Preserved fail-closed behavior for descriptors missing `data_path` when no
  shared market-data path is supplied.
- Added focused tests for same-path load reuse, distinct-path separation, and
  integrity mismatch before cached frame reuse.
- Updated the sandbox research contract and active index.

## Boundary

No candidate pack, paper/live artifact, order or sizing behavior, runtime-mode
change, live configuration write, provider download, strict-cycle execution,
source artifact mutation, validation execution, or promotion claim was added.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "market_frame_loader"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 12 focused loader tests passed.
- 118 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
