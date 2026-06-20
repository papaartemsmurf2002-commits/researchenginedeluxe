# WPR106-287 Sandbox Suite Input Cache

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Speed up archive-backed sandbox suite iteration by reusing parsed suite inputs
across sequential cases. Repeated references to the same sandbox run spec,
strategy catalog, or venue archive manifest should be parsed once inside a
sequential suite run, then reused as immutable descriptors for later cases.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-287-sandbox-suite-input-cache.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_SUITE_INPUT_CACHE_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/suite.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not execute strict validation, write candidate packs, create paper/live
  signals, define sizing, place orders, change runtime mode, write live
  configuration, download provider data, mutate source files, or claim
  promotion readiness.
- Preserve the 2024+ sandbox data rule.
- Preserve deterministic trial IDs, rankings, evidence-request descriptors,
  case ordering, market-source metadata, blocker semantics, and sandbox
  boundary flags.
- Cache only parsed descriptor inputs in process memory. Do not serialize cache
  contents into suite artifacts.
- Keep parallel suite execution case-local so concurrent cases do not mutate a
  shared input cache.

## Plan

1. Add a private suite input cache for parsed specs, strategy catalogs, and
   venue archive descriptors.
2. Use one input cache for sequential suite execution and isolated per-case
   caches for parallel execution.
3. Record cache scope metadata in suite manifests without serializing cached
   descriptors separately.
4. Add focused tests proving repeated sequential case paths are loaded once.
5. Update the sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Completion Notes

Implemented and closed on 2026-06-19. Added a private `_SuiteInputCache` that
caches parsed sandbox run specs, strategy catalogs, and venue archive
descriptors by resolved local path. Sequential suite execution now reuses one
input cache across cases, while parallel suite execution keeps caches
case-local. Suite manifests record `input_cache_scope`, but cached descriptors
remain process-local and are not serialized as separate artifacts.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "suite_reuses_input_cache or suite_reuses_market_data_cache or suite_runs_multiple_cases or suite_parallel_execution_preserves_case_order"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 4 focused suite cache tests passed, 124 sandbox tests passed,
package compileall passed, 11 import-boundary tests passed, and 461 contract
tests passed.
