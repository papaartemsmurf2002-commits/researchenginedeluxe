# WPR106-400 V2 Backtest Data Service

Status: closed
Owner: Codex Research Agent
Created: 2026-06-21

## Objective

Implement Phase 9 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`: add
the v2 backtest data service read path with deterministic local archive panel
loading, dynamic lockbox enforcement, earliest-date and usable-month gates,
coverage gate integration, as-of universe enforcement, per-request data
manifests, and focused benchmark-style service tests.

This packet does not implement strategy execution, the backtest engine, cost
modeling, ledgers, Lead Book storage, UI, paper/live behavior, order placement,
sizing, runtime-mode changes, candidate packs, or promotion behavior.

## Audit IDs

- `V2-AUD-BTDATA-001`

## Dependencies

- `docs/contracts/backtest_data_service_contract.md`
- `docs/contracts/validation_contract.md`
- `src/tradingbotsuite/v2/archive/**`
- `src/tradingbotsuite/v2/data_quality/**`
- `src/tradingbotsuite/v2/universe/**`
- `src/tradingbotsuite/v2/validation/**`

## Allowed Paths

- `docs/contracts/backtest_data_service_contract.md`
- `docs/contracts/validation_contract.md`
- `src/tradingbotsuite/v2/backtest_data/**`
- `src/tradingbotsuite/v2/validation/**`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/**`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-400-v2-backtest-data-service.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Backtest data reads must use local archive snapshots and manifests only.
- Do not call venue APIs or add direct provider reads from the service.
- Accepted/reported evidence must require an archive snapshot ID, as-of
  universe snapshot ID, coverage >= 0.98, earliest reported start on or after
  2024-01-01, and at least six usable months.
- Current universe snapshots are sandbox-only and must fail accepted/reported
  evidence reads.
- Ordinary accepted/reported requests must not overlap the dynamic latest
  full-calendar-month lockbox.
- Warmup data may be loaded separately from the reported PnL window, but it
  must not count as reported usable months.
- Do not create or modify candidate packs.
- Do not create paper/live artifacts.
- Do not place orders, change runtime mode, write live configuration, or add
  sizing/order-placement behavior.

## Acceptance Criteria

- Request overlapping the dynamic lockbox fails before strategy code can see a
  panel.
- Request before 2024-01-01 fails in reported/accepted mode.
- Request with fewer than six usable reported months fails in accepted mode.
- Current-universe evidence request fails.
- Valid request loads rows from the referenced archive snapshot and only the
  requested fields.
- Valid request writes/returns a deterministic data manifest.
- Warmup rows are counted separately from the reported PnL window.
- Low-coverage or sandbox coverage reports fail accepted/reported evidence.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

No broader non-v2 tests are required unless shared implementation files outside
the v2 shell are changed.

## Stop Conditions

- A no-touch live/runtime/order/sizing path must be modified.
- Strategy execution, a backtest runner, ledger append workflow, Lead Book
  store, candidate-pack, paper/live, order, sizing, runtime, or promotion
  behavior becomes necessary.
- The service cannot enforce archive snapshot, as-of universe, coverage, or
  lockbox gates using local manifests.

## Completion Notes

Closed on 2026-06-21.

- Added Phase 9 backtest-data schemas:
  - `BacktestDataRequest`
  - `BacktestDataManifest`
  - `BacktestDataSlice`
  - `BacktestEvidenceMode`
- Added the dynamic latest full-calendar-month lockbox calculator.
- Added `BacktestDataService.load_panel`, which:
  - enforces earliest reported start on or after 2024-01-01;
  - enforces six usable reported months for accepted/reported evidence;
  - rejects lockbox overlap before archive or strategy access;
  - requires a silver archive snapshot and matching local manifest files;
  - requires an as-of universe row for accepted/reported evidence;
  - rejects current-universe accepted/reported evidence;
  - requires coverage reports and wraps coverage-gate blockers as
    `BacktestDataError`;
  - reads only requested output fields plus internal `ts` filtering;
  - separates warmup rows from reported PnL-window row counts;
  - writes deterministic request manifests under
    `manifests/backtest_data_requests.parquet`.
- Added CLI `backtest-data load-panel` for local archive-backed smoke reads.
- Updated backtest-data and validation contracts.
- Marked `V2-AUD-BTDATA-001` as `self_checked`.
- No strategy execution, backtest runner, ledger append workflow, Lead Book
  storage, UI, paper/live behavior, order placement, sizing, runtime-mode
  changes, candidate-pack writing, or promotion behavior was implemented.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_backtest_data_phase9.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Result:

- Focused Phase 9 tests passed: 9 passed.
- Focused v2 tests passed: 63 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- Full `compileall` for `src\tradingbotsuite` passed.
- Contract tests passed: 462 passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
