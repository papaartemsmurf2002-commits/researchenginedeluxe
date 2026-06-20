# WPR106-283 Sandbox Descriptor Market Frame Load Cache

Status: closed
Owner: Codex Research Agent
Created: 2026-06-19

## Objective

Speed up archive-backed sandbox setup by loading and normalizing identical
descriptor `data_path` files once per descriptor batch, while still verifying
source integrity for every descriptor before cached frames are reused.

## Scope

- Add a local load cache to descriptor-routed market-frame batch loading keyed
  by normalized resolved source path.
- Preserve shared-market-data smoke semantics.
- Preserve per-descriptor `source_integrity` verification before cache reuse.
- Preserve fail-closed behavior for descriptors without `data_path` when no
  shared market-data path is supplied.
- Preserve separate loads and frame objects for distinct descriptor paths.
- Add focused tests proving same-path load reuse and integrity-before-cache
  behavior.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-283-sandbox-descriptor-market-frame-load-cache.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_DESCRIPTOR_MARKET_FRAME_LOAD_CACHE_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/market_data.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Descriptor-routed batch loading reads and normalizes an identical descriptor
  `data_path` once for multiple descriptors.
- Every descriptor with `source_integrity` metadata is checked before a cached
  frame can be returned for that descriptor.
- Distinct descriptor paths continue to load as distinct market frames.
- Missing descriptor `data_path` behavior remains fail-closed.
- No candidate packs, paper/live signals, sizing, order placement, strict
  validation execution, provider downloads, source artifact mutation, runtime
  mode changes, or live configuration writes are introduced.
- Validation includes focused loader tests, full sandbox tests, package compile,
  import-boundary tests, and the contract baseline when the local environment
  allows it.

## Boundary

This packet only changes research-sandbox market-data batch loading. It does
not change backtest assumptions, execute strict validation, write candidate
artifacts, create paper/live signals, define sizing, place orders, mutate
runtime mode, write live configuration, mutate source archive files, download
provider data, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-19. Descriptor-routed market-frame batch
loading now resolves descriptor `data_path` values to a stable cache key and
loads/normalizes identical source files once per batch. A batch-local
file-integrity cache avoids repeated hashing of the same local source, while
each descriptor's expected `source_integrity` metadata is still evaluated
before any cached frame is returned for that descriptor. Distinct resolved
paths still load as distinct frames, and missing descriptor data paths still
fail closed when no shared market-data path is supplied.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "market_frame_loader"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 12 focused loader tests passed, 118 sandbox tests passed,
package compileall passed, 11 import-boundary tests passed, and 461 contract
tests passed.
