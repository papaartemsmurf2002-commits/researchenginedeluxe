# WPR106-305 Sandbox Direct Workbook Sheet Provenance

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Preserve workbook sheet provenance for direct strategy catalog rows loaded from
local `.xlsx/.xls` workbooks, especially when a human spreadsheet does not
provide an explicit source ID.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-305-sandbox-direct-workbook-sheet-provenance.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_DIRECT_WORKBOOK_SHEET_PROVENANCE_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/intake.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not execute strict validation, write candidate packs, create paper/live
  signals, define sizing, place orders, change runtime mode, write live
  configuration, download provider data, mutate source workbook files, or claim
  promotion readiness.
- Preserve non-workbook direct catalog row behavior unless the row already
  carries a `source_sheet` column from workbook intake.
- Treat direct workbook sheet provenance as descriptor metadata only.
- Do not alter sweep execution, preflight trial estimates, ranking math,
  blocker semantics, evidence-request selection, or archive routing.

## Plan

1. Update direct strategy row parsing so workbook-provided `source_sheet`
   contributes to the default `source_id` when no explicit source ID is present.
2. Preserve explicitly supplied `source_id` values exactly.
3. Add focused loader/materializer regressions for direct multi-sheet workbook
   provenance.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after confirming spreadsheet-like lead workbook
  rows already preserve `source_path#source_sheet`, while direct workbook rows
  without explicit source IDs still default to the workbook path only.
- 2026-06-19: Updated direct strategy row parsing so workbook-provided
  `source_sheet` contributes to the default `source_id` only when no explicit
  source ID is present.
- 2026-06-19: Added a no-engine XLSX fallback regression proving direct
  multi-sheet source IDs survive loader and materializer round trips.

## Completion Notes

Implemented and closed on 2026-06-19. Direct strategy rows loaded from local
workbooks now default to `workbook_path#sheet_name` when the row does not
provide an explicit source ID. Explicit source IDs such as `Catalog Source`
remain authoritative and unchanged. Materialized strategy catalog rows and
source build reports preserve those direct workbook sheet source IDs.

This is descriptor provenance only. Non-workbook direct catalog behavior is
unchanged, and the packet did not alter sweep execution, preflight trial
estimates, trial metrics, rankings, evidence-request selection, archive
routing, strict validation behavior, candidate-pack behavior, live/paper signal
state, sizing, order placement, runtime mode, live config, provider access, or
promotion state.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "direct_workbook_sheet_source_ids"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "strategy_catalog_loader or strategy_catalog_materializer"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 1 focused direct workbook provenance test passed, 12 strategy
catalog loader/materializer tests passed, 169 sandbox tests passed, package
compileall passed, 11 import-boundary tests passed, and 461 contract tests
passed.
