# WPR106-285 Sandbox Iteration Market Data Cache

Status: closed
Owner: Codex Research Agent
Created: 2026-06-19

## Objective

Speed up one-command archive-backed sandbox iterations by sharing a bounded
in-memory market-data read cache across archive coverage, compatibility
preflight, and the archive sweep, so the same local source file is not read and
normalized repeatedly inside one iteration.

## Scope

- Add a reusable sandbox market-data cache object for normalized frames and
  source-integrity reads.
- Allow archive audit/coverage, compatibility preflight, and archive sweep to
  accept an optional cache.
- Pass one cache through `run_sandbox_agent_iteration` from coverage through
  preflight and sweep.
- Preserve descriptor-specific source-integrity checks, routing metadata,
  row/blocker semantics, trial IDs, rankings, and evidence-request descriptors.
- Keep the cache process-local and out of JSON/Parquet artifacts.
- Add focused tests proving one-command iteration reuses a source read across
  coverage/preflight/sweep and still blocks bad descriptors before cached frame
  use.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-285-sandbox-iteration-market-data-cache.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_MARKET_DATA_CACHE_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/market_data.py`
- `src/tradingbotsuite/research_sandbox/archive_audit.py`
- `src/tradingbotsuite/research_sandbox/archive_coverage.py`
- `src/tradingbotsuite/research_sandbox/preflight.py`
- `src/tradingbotsuite/research_sandbox/runner.py`
- `src/tradingbotsuite/research_sandbox/iteration.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- A one-command sandbox iteration with one descriptor source reads and
  normalizes that source once across coverage, preflight, and sweep.
- Archive sweep can consume a caller-supplied cache without changing trial
  identity, rankings, or market-source metadata.
- A descriptor with mismatched source integrity still blocks before cached
  frame use.
- Existing cached-iteration reuse, blocked-preflight behavior, shared-market
  smoke semantics, and sandbox boundary flags remain stable.
- No candidate packs, paper/live signals, sizing, order placement, strict
  validation execution, provider downloads, source artifact mutation, runtime
  mode changes, or live configuration writes are introduced.
- Validation includes focused cache tests, full sandbox tests, package compile,
  import-boundary tests, and the contract baseline when the local environment
  allows it.

## Boundary

This packet only changes process-local market-data reuse inside research
sandbox commands. It does not change backtest assumptions, execute strict
validation, write candidate artifacts, create paper/live signals, define
sizing, place orders, mutate runtime mode, write live configuration, mutate
source archive files, download provider data, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-19. Added `SandboxMarketDataCache` for
process-local normalized-frame and source-integrity reuse. Archive
audit/coverage, compatibility preflight, and archive sweep now accept an
optional cache, and one-command sandbox iterations pass one cache through
coverage, preflight, and sweep. A one-command iteration with a single local
descriptor source now reads and normalizes that source once across the active
iteration path. The cache is not serialized into artifacts and does not change
trial IDs, rankings, market-source metadata, blocker semantics, or boundary
flags.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "market_data_cache or cache_across_steps or archive_sweep_uses_preloaded or market_frame_loader or readiness_caches"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 15 focused cache tests passed, 122 sandbox tests passed,
package compileall passed, 11 import-boundary tests passed, and 461 contract
tests passed.
