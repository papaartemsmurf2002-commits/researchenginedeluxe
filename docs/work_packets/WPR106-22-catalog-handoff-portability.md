# WPR106-22 Catalog Handoff Portability

Status: closed

## Scope

Resolve the actionable R106 catalog handoff P1 found by WPR106-21 without
rewriting generated data. The migrated `main` checkout must be able to reuse an
active historical-data catalog whose recorded absolute paths still point at the
old checkout, while preserving research-only boundaries and truthful inactive
provider status.

`ISSUE-R104-001` remains an empirical evidence gate and is out of scope for
this code packet unless the required long ETH cycle/discovery and downstream
eligibility evidence is produced separately.

## Allowed paths

- `docs/work_packets/WPR106-22-catalog-handoff-portability.md`
- `docs/stage_reports/STAGE_R106_CATALOG_HANDOFF_PORTABILITY_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/data/historical_data_catalog.py`
- `src/tradingbotsuite/operator_console.py`
- `tests/tradingbotsuite/test_market_data_collection.py`
- `tests/tradingbotsuite/test_operator_ui.py`

## Constraints

- Do not edit generated fixture packs, catalog artifacts, cycle outputs,
  discovery ledgers, or active generated specs.
- Preserve `research_only`, `observe_only`, and `promotion_ready: false`.
- Do not change live runtime mode, live configuration, sizing, order placement,
  or promotion readiness.
- Do not mark `ISSUE-R104-001` resolved without empirical evidence.

## Acceptance

- Stale absolute catalog paths from a prior checkout are rebased to the current
  catalog run directory when the mirrored artifact path exists.
- Operator default research jobs can use the active catalog specs after repo
  migration without accepting paths outside the research output directory.
- Catalog diagnostics still report inactive providers truthfully and preserve
  research-only boundary flags.
- `ISSUE-R106-003` is resolved or narrowed according to validation evidence.
- Validation commands and outcomes are recorded in the stage report.

## Planned validation

- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`

## Closeout

- Added read-time historical-data catalog path rebasing for migrated
  operator-run artifacts when the current mirrored file or parent path exists.
- Updated operator catalog diagnostics/artifact indexing to consume normalized
  catalog payloads.
- Updated isolated historical-cycle and discovery job setup so copied active
  specs with stale embedded paths are normalized before per-job specs are
  written.
- Added regressions for migrated catalog path fields, default active-catalog
  spec routing, and isolated cycle/discovery payload normalization.
- Resolved `ISSUE-R106-003`; `ISSUE-R104-001` remains open because it requires
  empirical ETH/candidate-gate evidence, not a code-only fix.
- Validation passed:
  - `python -m compileall -q src\tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
