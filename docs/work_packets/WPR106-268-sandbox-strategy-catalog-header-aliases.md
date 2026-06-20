# WPR106-268 Sandbox Strategy Catalog Header Aliases

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Make existing strategy spreadsheets and CSV catalogs easier to ingest by
normalizing common direct-catalog header aliases before falling back to
spreadsheet lead proxy compilation.

## Scope

- Extend sandbox strategy catalog loading to recognize common aliases for
  direct strategy fields such as hypothesis ID, family, signal column, side,
  source ID, exit profile, filters, params, tags, and notes.
- Preserve exact canonical direct catalog behavior and spreadsheet-like lead
  proxy behavior.
- Keep direct precomputed-signal catalogs as descriptor rows; do not generate
  strategy math, live signals, or candidate evidence.
- Add focused sandbox tests for alias-heavy direct strategy spreadsheets.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-268-sandbox-strategy-catalog-header-aliases.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_STRATEGY_CATALOG_HEADER_ALIASES_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/intake.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- A direct strategy catalog with common spreadsheet headers such as
  `Hypothesis`, `Strategy Family`, `Signal`, and `Direction` loads as direct
  `StrategyCatalogRow` descriptors, not as blueprint proxy lead rows.
- Optional fields such as source ID, filters, params, tags, and notes survive
  alias normalization.
- Canonical direct catalogs and existing spreadsheet-like lead catalogs keep
  their current behavior.
- Validation includes focused strategy-catalog tests, full sandbox tests,
  package compile, import-boundary tests, and the contract baseline when the
  local environment allows it.

## Boundary

This packet only improves local strategy catalog parsing for sandbox descriptor
intake. It does not execute sandbox sweeps, execute strict validation, write
candidate artifacts, change strategy math, create paper/live signals, define
sizing, place orders, mutate runtime mode, write live configuration, download
provider data, mutate source archive files, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. Added direct strategy catalog header
alias normalization before spreadsheet lead/proxy fallback. Alias-heavy sheets
with direct precomputed signal columns now load as direct `StrategyCatalogRow`
descriptors, and optional source, exit, filter, params, tags, and notes fields
are preserved.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "strategy_catalog"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py -q -k "provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest"
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q -k "not provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest"
```

Final results: 10 focused strategy-catalog tests passed, 98 sandbox tests
passed, package compileall passed, 11 import-boundary tests passed, the
isolated affected async contract test passed once, and the non-affected
contract baseline passed with 460 tests and 1 deselected. Full one-shot
contract attempts reached 460 passed tests before known `ISSUE-R106-026`
Windows `WinError 10055` during pytest-asyncio event-loop socketpair setup
before the affected async test body.
