# WPR106-303 Sandbox Workbook Strategy Catalog Sheets

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Load every usable sheet from local workbook strategy catalogs instead of
stopping at the first usable sheet, and report compact workbook sheet
diagnostics in strategy-catalog materializer build artifacts for faster agent
preflight loops.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-303-sandbox-workbook-strategy-catalog-sheets.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_WORKBOOK_STRATEGY_CATALOG_SHEETS_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/intake.py`
- `src/tradingbotsuite/research_sandbox/strategy_catalog_materializer.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not execute strict validation, write candidate packs, create paper/live
  signals, define sizing, place orders, change runtime mode, write live
  configuration, download provider data, mutate source workbook files, or claim
  promotion readiness.
- Preserve the 2024+ sandbox date floor, archive routing, source-integrity
  checks, deterministic trial identity, ranking math, blocker semantics,
  eligibility flags, and evidence-request selection.
- Treat workbook sheet names, row counts, and included/skipped sheet summaries
  as descriptor navigation metadata only.
- Keep workbook diagnostics bounded and deterministic for compact agent
  handoff artifacts.

## Plan

1. Add workbook sheet enumeration that works with both pandas Excel engines and
   the existing built-in `.xlsx` fallback parser.
2. Combine every usable direct strategy sheet and spreadsheet-like lead sheet
   into one load result while preserving sheet provenance.
3. Add compact workbook sheet diagnostics to materializer source rows and
   Parquet build reports.
4. Add focused workbook loader/materializer regressions for multi-sheet direct
   and lead catalogs.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after confirming the current workbook loader stops
  at the first usable sheet and materializer reports only file-level source
  status.
- 2026-06-19: Added diagnostic-aware strategy catalog loading for local
  workbooks, preserving the public `load_strategy_catalog()` row API while
  allowing materializers to surface workbook sheet summaries.
- 2026-06-19: Added no-engine XLSX fallback tests for multi-sheet direct/lead
  aggregation and materializer JSON/Parquet sheet diagnostics.

## Completion Notes

Implemented and closed on 2026-06-19. Local `.xlsx/.xls` strategy catalog
intake now loads every usable workbook sheet instead of stopping at the first
usable sheet. Direct strategy sheets and spreadsheet-like lead sheets are
aggregated into one strategy list; unsupported or notes-only sheets are skipped
and reported. Materializer build rows and Parquet reports now include compact
workbook diagnostics: sheet count, included/skipped counts, strategy count,
status/kind counts, bounded sheet-name lists, and bounded per-sheet rows with
skip reasons.

Workbook sheet diagnostics are navigation metadata only. The packet did not
execute strategy sweeps, strict validation, candidate-pack creation, live/paper
signal creation, sizing, order placement, runtime-mode changes, live config
writes, provider downloads, or source workbook mutation.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "workbook_sheet or all_usable_xlsx"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "strategy_catalog_loader or strategy_catalog_materializer"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 2 focused workbook tests passed, 11 strategy catalog
loader/materializer tests passed, 167 sandbox tests passed, package compileall
passed, 11 import-boundary tests passed, and 461 contract tests passed.
