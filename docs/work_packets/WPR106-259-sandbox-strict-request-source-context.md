# WPR106-259 Sandbox Strict Request Source Context

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Make sandbox evidence-request handoffs more agent-ready by carrying compact
source-trial context directly on each descriptor. A later strict-validation
agent should be able to see the trial, venue descriptor, data window, market
source, exit/filter assumptions, and sandbox metrics without reopening ranking
Parquet files.

## Scope

- Add compact source-trial context to sandbox evidence-request descriptors.
- Project that context into strict-validation request bundle descriptor rows.
- Preserve descriptor-only behavior: no strict validation execution and no
  candidate-pack writes.
- Add focused tests proving run requests and bundle rows carry the source
  context while preserving sandbox boundary flags.
- Update the sandbox contract, active index, stage ledger, and stage report.

## Allowed Paths

- `docs/work_packets/WPR106-259-sandbox-strict-request-source-context.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_STRICT_REQUEST_SOURCE_CONTEXT_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/evidence_request.py`
- `src/tradingbotsuite/research_sandbox/validation_bundle.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Evidence requests include a compact `source_trial_context` object with trial
  execution assumptions, market timestamp bounds, descriptor/source routing
  metadata, and sandbox boundary-safe values.
- Strict-validation request bundle rows expose the same context at a stable
  top-level field so agents can inspect bundle Parquet/JSON without reopening
  rankings.
- Request IDs remain deterministic for the same source run/trial validation
  request identity.
- Bundles remain descriptor-only and explicitly record no strict-validation
  execution, no candidate-pack writes, no paper/live signals, no sizing, no
  order placement, and no runtime-mode change.
- Validation includes focused sandbox tests, import-boundary tests, package
  compile, and the contract baseline when the local validation environment
  allows pytest-asyncio socket setup.

## Boundary

This packet changes sandbox handoff metadata only. It does not execute strict
validation, change strategy math, change trial scoring or ranking, change trial
IDs, write candidate packs, create paper/live signals, define sizing, place
orders, change runtime mode, write live configuration, download provider data,
mutate source archive files, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. Sandbox evidence requests now include a
compact `source_trial_context` object with source run/trial identity,
hypothesis/family/source ID, venue, symbol, data family, signal column, side,
holding period, exit/filter variant IDs, market timestamp bounds, descriptor
routing metadata, and sandbox execution assumptions.

Strict-validation request bundle rows preserve the same context and expose
source venue descriptor ID, source market start/end, and source market-source
routing metadata as stable row fields for agent inspection. Request IDs remain
based on source run ID, source trial ID, and requested validation type.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "archive_sweep_routes_each_venue or validation_request_bundle"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 3 focused sandbox tests passed, 86 sandbox tests passed,
package compileall passed, 11 import-boundary tests passed, and the full
contract baseline passed with 461 tests.
