# WPR106-397 V2 Data Quality And Coverage Service

Status: closed
Owner: Codex Research Agent
Created: 2026-06-20

## Objective

Implement Phase 6 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`: add
data coverage and quality reporting for v2 archive-backed market-data slices,
including expected-row calculators, gap/duplicate/stale/zero-volume/outlier
checks, coverage manifest storage, CLI reporting, and a backtest-data coverage
gate integration point.

This packet does not implement collectors, backtests, strategies, ledgers, Lead
Book storage, UI, paper/live behavior, order placement, sizing, runtime-mode
changes, candidate packs, or promotion behavior.

## Audit IDs

- `V2-AUD-QUAL-001`
- `V2-AUD-BTDATA-001` only for the coverage-gate integration point

## Dependencies

- `docs/contracts/data_quality_contract.md`
- `docs/contracts/backtest_data_service_contract.md`
- `src/tradingbotsuite/v2/archive/layout.py`
- `src/tradingbotsuite/v2/archive/manifest_store.py`
- `src/tradingbotsuite/v2/universe/**`

## Allowed Paths

- `docs/contracts/data_quality_contract.md`
- `docs/contracts/backtest_data_service_contract.md`
- `src/tradingbotsuite/v2/data_quality/**`
- `src/tradingbotsuite/v2/backtest_data/**`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/**`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-397-v2-data-quality-and-coverage-service.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Do not create or modify candidate packs.
- Do not create paper/live artifacts.
- Do not place orders, change runtime mode, write live configuration, or add
  sizing/order-placement behavior.
- Coverage below `0.98` must fail accepted/reported evidence mode.
- Sandbox diagnostic exceptions must be labeled non-evidence.
- Missing data must be reported as missing, not filled or silently repaired.
- Backtest-data work is limited to a coverage gate integration point; no full
  data service implementation is in scope.

## Acceptance Criteria

- Expected bar-row counts are deterministic by timeframe.
- Coverage reports are queryable by instrument/date/timeframe.
- Missing days are reported explicitly.
- Duplicate timestamps, stale segments, zero volume, and outlier checks are
  surfaced in report rows.
- Coverage below `0.98` fails accepted/reported evidence mode.
- Sandbox diagnostic exceptions are labeled non-evidence.
- CLI commands exist for `redx data coverage` and
  `redx data quality-report`.
- A backtest-data coverage gate can reject insufficient accepted-evidence
  coverage before strategy code exists.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
git diff --check
```

No broad non-v2 tests are required unless shared implementation files outside
the v2 shell are changed.

## Stop Conditions

- A no-touch live/runtime/order/sizing path must be modified.
- A real collector, backtest runner, strategy executor, ledger append workflow,
  Lead Book store, candidate-pack, paper/live, order, sizing, runtime, or
  promotion behavior becomes necessary.

## Completion Notes

Closed on 2026-06-20.

- Added `CoverageReport`, `DataQualityCheck`, `EvidenceMode`, and
  `QualityStatus` schemas with the v2 research-only boundary preserved.
- Added deterministic timeframe parsing, expected bar counts, expected timestamp
  iteration, and bar coverage reports over `[start_ts, end_ts)` windows.
- Coverage ratio uses unique timestamps so duplicates cannot inflate coverage.
- Reports record missing timestamp counts, missing timestamp samples, and
  explicit `missing_days`.
- Added duplicate timestamp, zero-volume, stale-segment, return-outlier,
  spread-outlier, and funding-outlier checks.
- Added `CoverageManifestStore` for local archive-backed
  `data_coverage.parquet` and `data_quality_checks.parquet` manifests.
- Added query support by venue, instrument, family, timeframe, and date.
- Added `redx data coverage` and `redx data quality-report` CLI commands for
  local Parquet inputs.
- Added `require_coverage_for_evidence` as the Phase 6 coverage-gate integration
  point for the future backtest data service.
- Coverage below `0.98` fails accepted/reported evidence mode.
- Sandbox diagnostic low coverage is labeled
  `sandbox_diagnostic_non_evidence` and remains non-evidence.
- Marked `V2-AUD-QUAL-001` as `self_checked`.
- Left `V2-AUD-BTDATA-001` planned because the full lockbox-aware backtest data
  service is still future Phase 8 work.
- No collectors, backtests, strategies, ledgers, Lead Book storage, UI,
  paper/live behavior, order placement, sizing, runtime-mode changes,
  candidate-pack writing, or promotion behavior was implemented.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Result:

- Focused v2 tests passed: 42 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- Full `compileall` for `src\tradingbotsuite` passed.
- Contract tests passed: 462 passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
