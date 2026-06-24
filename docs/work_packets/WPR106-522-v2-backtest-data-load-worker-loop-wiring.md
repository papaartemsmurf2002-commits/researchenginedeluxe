# WPR106-522 - V2 Backtest Data Load Worker Loop Wiring

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-BTDATA-005`
- `V2-AUD-WORKER-028`
- `V2-AUD-AUTONOMY-017`

## Objective

Add an explicit durable `backtest_data_load` worker stage and wire it into the
bounded research-cycle order between `strategy_queue_scan` and
`vectorized_backtest`. The stage must call the canonical
`BacktestDataService.load_panel()` path, return archive/universe/coverage/data
manifest refs, and allow later vectorized backtests to bind and verify those
refs before running.

This packet does not add collectors, download market data, write gold panels,
run live/paper systems, place orders, emit sizing instructions, create
candidate evidence, create candidate packs, change runtime mode, or make
promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-522-v2-backtest-data-load-worker-loop-wiring.md`
- `src/tradingbotsuite/v2/backtest_data/jobs.py`
- `src/tradingbotsuite/v2/backtest_data/__init__.py`
- `src/tradingbotsuite/v2/backtest_engine/jobs.py`
- `src/tradingbotsuite/v2/workers/models.py`
- `src/tradingbotsuite/v2/workers/runner.py`
- `src/tradingbotsuite/v2/autonomy/cycle_planner.py`
- `src/tradingbotsuite/v2/autonomy/cycle_fixture.py`
- `src/tradingbotsuite/v2/autonomy/cycle_public.py`
- `docs/contracts/backtest_data_service_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/contracts/autonomy_loop_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_workers_phase7.py`
- `tests/v2/test_autopilot_research_cycle_phase26.py`
- `tests/v2/test_autopilot_research_cycle_runner_phase27.py`
- `tests/v2/test_autopilot_fixture_cycle_phase28.py`
- `tests/v2/test_autopilot_public_cycle_phase30.py`
- `tests/v2/test_autopilot_scheduler_phase33.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No provider/API download behavior or collector implementation changes.
- No strategy logic, ledger semantics, Lead Book scoring, validation policy, or
  audit-report scoring changes beyond required worker-stage evidence prefixes.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py tests/v2/test_autopilot_research_cycle_phase26.py tests/v2/test_autopilot_research_cycle_runner_phase27.py tests/v2/test_autopilot_fixture_cycle_phase28.py tests/v2/test_autopilot_public_cycle_phase30.py tests/v2/test_autopilot_scheduler_phase33.py -q
```

Baseline:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Add `WorkerJobKind.BACKTEST_DATA_LOAD` and route it through the durable
  worker runner.
- Add a `run_backtest_data_job()` handler that constructs `BacktestDataRequest`
  from worker input, calls `BacktestDataService.load_panel()`, writes the
  canonical data manifest, and returns deterministic output refs.
- Add optional expected data refs to durable vectorized backtest jobs so a
  cycle can bind `data_manifest_id`, `coverage_report_id`,
  `archive_snapshot_id`, and `universe_snapshot_id` from the explicit load
  stage and fail closed on mismatch.
- Update bounded-cycle required stage ordering and generated fixture/public
  cycle specs to include `backtest_data_load` between strategy queue and
  vectorized backtest.

## Acceptance Criteria

- Standalone `backtest_data_load` workers load only through
  `BacktestDataService` and surface data manifest, coverage, archive, and
  universe refs.
- Bounded cycle planning requires `strategy_queue_scan -> backtest_data_load ->
  vectorized_backtest -> validation_gate -> ledger_append_export ->
  lead_book_upsert -> audit_check`.
- Generated fixture and public diagnostic cycle specs bind backtest-data refs
  into vectorized backtest specs.
- Vectorized backtest jobs reject mismatched expected data refs before
  declaring worker success.
- All outputs preserve canonical v2 research-only invariants and remain
  non-promotable, not candidate evidence, not candidate-pack eligible, not
  paper/live signals, not sizing/order instructions, and not runtime changes.

## Validation Evidence

Focused:

```text
python -m compileall -q src/tradingbotsuite: passed
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py tests/v2/test_autopilot_research_cycle_phase26.py tests/v2/test_autopilot_research_cycle_runner_phase27.py tests/v2/test_autopilot_fixture_cycle_phase28.py tests/v2/test_autopilot_public_cycle_phase30.py tests/v2/test_autopilot_scheduler_phase33.py -q: 87 passed
```

Baseline:

```text
python -m compileall -q src/tradingbotsuite: passed
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q: 543 passed
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```
