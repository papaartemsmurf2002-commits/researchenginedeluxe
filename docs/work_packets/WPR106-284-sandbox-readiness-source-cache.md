# WPR106-284 Sandbox Readiness Source Cache

Status: closed
Owner: Codex Research Agent
Created: 2026-06-19

## Objective

Speed up archive-backed sandbox readiness loops by reusing identical local
market-source loads and source-integrity reads across archive audit/coverage
and compatibility preflight, while preserving descriptor-scoped blocker
semantics.

## Scope

- Add a reusable cached source-integrity error helper for descriptor batches.
- Cache archive audit market-frame loads by normalized resolved source path.
- Cache compatibility preflight loaded/materialized market frames by normalized
  resolved source path inside one preflight run.
- Preserve per-descriptor source-integrity checks before any cached market data
  is used.
- Preserve shared-market-data smoke semantics, missing-path blockers,
  requested-window blockers, 2024+ filtering, trial estimates, and
  descriptor-specific rows.
- Add focused tests proving audit/preflight same-source reuse and
  integrity-before-cache behavior.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-284-sandbox-readiness-source-cache.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_READINESS_SOURCE_CACHE_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/market_data.py`
- `src/tradingbotsuite/research_sandbox/archive_audit.py`
- `src/tradingbotsuite/research_sandbox/preflight.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Archive descriptor audit reads and normalizes an identical descriptor
  `data_path` once for multiple descriptors in one audit.
- Compatibility preflight reads, normalizes, windows, and materializes
  identical descriptor sources once per preflight run.
- Source integrity remains descriptor-scoped: a bad descriptor sharing a cached
  source still blocks before receiving cached market data.
- Existing ready/blocked counts, requested-window behavior, shared-market-data
  smoke behavior, and sandbox boundary flags remain stable.
- No candidate packs, paper/live signals, sizing, order placement, strict
  validation execution, provider downloads, source artifact mutation, runtime
  mode changes, or live configuration writes are introduced.
- Validation includes focused readiness cache tests, full sandbox tests,
  package compile, import-boundary tests, and the contract baseline when the
  local environment allows it.

## Boundary

This packet only changes research-sandbox readiness-path caching. It does not
change backtest assumptions, execute strict validation, write candidate
artifacts, create paper/live signals, define sizing, place orders, mutate
runtime mode, write live configuration, mutate source archive files, download
provider data, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-19. Archive descriptor audit now caches
loaded and normalized market frames by resolved source path inside one audit,
and compatibility preflight caches loaded/windowed/materialized market frames
by resolved source path inside one preflight run. A shared cached
source-integrity helper avoids repeated same-file hashing while still
evaluating every descriptor's expected `source_integrity` metadata before
cached market data is used. Distinct source paths, descriptor rows, routing
metadata, requested-window blockers, and trial estimates remain separate.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "readiness_caches or reuse_identical_descriptor_sources or market_frame_loader"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "archive_descriptor_audit or archive_audit_and_preflight or readiness_caches or preflight_reuses or cli_command_preflights"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 14 focused cache tests passed, 8 archive/preflight-focused tests
passed, 120 sandbox tests passed, package compileall passed, 11
import-boundary tests passed, and 461 contract tests passed.
