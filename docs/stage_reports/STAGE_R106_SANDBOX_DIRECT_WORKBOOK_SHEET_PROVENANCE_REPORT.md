# Stage R106 Sandbox Direct Workbook Sheet Provenance Report

Date: 2026-06-19
Packet: `docs/work_packets/WPR106-305-sandbox-direct-workbook-sheet-provenance.md`
Status: closed

## Summary

WPR106-305 preserves sheet provenance for direct strategy rows loaded from
local workbook strategy catalogs. When a direct `.xlsx/.xls` workbook row does
not provide an explicit source ID, sandbox intake now defaults the row
`source_id` to `workbook_path#sheet_name`. Rows that provide an explicit source
ID through fields such as `Catalog Source` remain unchanged.

This brings direct workbook sheets in line with spreadsheet-like lead workbook
rows, which already carry `source_path#source_sheet` provenance. Materialized
strategy catalogs and build reports now preserve those default direct workbook
sheet source IDs.

## Boundary

All outputs remain research-only, observe-only, sandbox-only, and
`promotion_ready: false`. Direct workbook sheet source IDs are descriptor
provenance only. This packet did not alter non-workbook direct catalog
behavior, sweep execution, preflight trial estimates, trial metrics, rankings,
evidence-request selection, archive routing, strict validation behavior,
candidate-pack behavior, live/paper signals, sizing, order placement, runtime
mode, live configuration, provider access, source workbook files, or promotion
state.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "direct_workbook_sheet_source_ids"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "strategy_catalog_loader or strategy_catalog_materializer"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 1 focused direct workbook provenance test passed.
- 12 strategy catalog loader/materializer tests passed.
- 169 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
