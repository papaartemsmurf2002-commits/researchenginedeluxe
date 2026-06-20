# WPR106-286 Sandbox Suite Market Data Cache

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Speed up archive-backed sandbox suite iteration by reusing one process-local
`SandboxMarketDataCache` across sequential suite cases. This should avoid
re-reading and re-normalizing the same resolved local market source when a
suite intentionally runs several cases over the same archive data.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-286-sandbox-suite-market-data-cache.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_SUITE_MARKET_DATA_CACHE_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/suite.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not write candidate packs, paper/live artifacts, sizing instructions,
  order instructions, runtime-mode changes, live configuration, or promotion
  claims.
- Preserve the 2024+ sandbox date floor.
- Preserve deterministic trial IDs, rankings, evidence-request descriptors,
  suite case ordering, and descriptor market-source metadata.
- Cache only in process memory. Do not serialize cached frames or integrity
  state into suite artifacts.
- Keep parallel suite execution case-local so concurrent cases do not mutate a
  shared cache.

## Plan

1. Thread an optional `SandboxMarketDataCache` through suite case preflight and
   archive sweep execution.
2. Use one shared cache for sequential suite execution and isolated per-case
   caches for parallel execution.
3. Add a regression test proving two sequential suite cases over the same
   local source read the source once across preflight and sweep.
4. Document the suite cache rule and packet evidence.
5. Run focused sandbox validation plus compile/contracts baseline.

## Completion Notes

Implemented and closed on 2026-06-19. `run_sandbox_suite` now passes one
process-local `SandboxMarketDataCache` across sequential suite cases and uses
isolated per-case caches for parallel suite execution. Each case passes its
cache through compatibility preflight and archive sweep execution. Suite
manifests record the cache scope as `suite_sequential` or
`case_local_parallel`, but cached frames and integrity state remain in memory
only.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "suite_reuses_market_data_cache or suite_runs_multiple_cases or suite_parallel_execution_preserves_case_order"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 3 focused suite-cache tests passed, 123 sandbox tests passed,
package compileall passed, 11 import-boundary tests passed, and 461 contract
tests passed.
