# WPR106-290 Sandbox Numeric Timestamp Unit Normalizer

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Prevent valid 2024+ local venue exports from being dropped during sandbox
normalization because numeric `timestamp`-like columns are interpreted with the
wrong epoch unit. The market-data loader should infer seconds, milliseconds,
microseconds, and nanoseconds consistently for all timestamp aliases, including
literal `timestamp`, `time`, `ts`, `open_time`, and venue-specific aliases.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-290-sandbox-numeric-timestamp-unit-normalizer.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_NUMERIC_TIMESTAMP_UNIT_NORMALIZER_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/market_data.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not execute strict validation, write candidate packs, create paper/live
  signals, define sizing, place orders, change runtime mode, write live
  configuration, download provider data, mutate source files, or claim
  promotion readiness.
- Preserve the 2024+ sandbox date floor and completed-row normalization.
- Preserve deterministic archive descriptor IDs, trial IDs, rankings,
  evidence-request descriptors, blocker semantics, and sandbox boundary flags.
- Keep parsing deterministic from local data only.

## Plan

1. Add a numeric epoch-unit inference helper for seconds/milliseconds/
   microseconds/nanoseconds.
2. Apply it to all timestamp aliases when the column is numeric.
3. Preserve string timestamp parsing for ISO-like or nonnumeric values.
4. Add focused tests for `timestamp` milliseconds, `time` microseconds, and
   archive manifest inclusion with numeric millisecond timestamps.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Completion Notes

Implemented and closed on 2026-06-19. Numeric timestamp aliases now infer Unix
epoch units by magnitude across seconds, milliseconds, microseconds, and
nanoseconds before the 2024+ sandbox filter is applied. The same parser covers
literal `timestamp`, `time`, `ts`, `open_time`, `startTime`, and other accepted
timestamp aliases. ISO/string parsing remains unchanged, and compact
`YYYYMMDD` values are preserved as calendar dates.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "numeric_timestamp or numeric_time or compact_yyyymmdd"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 4 focused timestamp tests passed, 134 sandbox tests passed,
package compileall passed, 11 import-boundary tests passed, and 461 contract
tests passed.
