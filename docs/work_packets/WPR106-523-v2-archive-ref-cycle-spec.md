# WPR106-523 - V2 Existing Archive Ref Cycle Spec

Status: self_checked
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-AUTONOMY-018`
- `V2-AUD-COLLECT-021`

## Objective

Add a bounded research-cycle spec writer for already-built local archive refs.
The spec must let operators point the durable loop at an existing
`archive_snapshot_id`, `universe_snapshot_id`, and local JSON/YAML strategy
directory without re-collecting data. Existing refs must be validated through
durable worker stages before later coverage, backtest-data, vectorized
backtest, validation, ledger, Lead Book, and audit stages consume them.

This packet does not download provider data, write market archive rows, write
gold panels, change strategy logic, run live/paper systems, place orders, emit
sizing instructions, create candidate packs, change runtime mode, or make
promotion/readiness claims.

## Allowed Paths

- `docs/work_packets/WPR106-523-v2-archive-ref-cycle-spec.md`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `src/tradingbotsuite/v2/autonomy/cycle_archive.py`
- `src/tradingbotsuite/v2/autonomy/__init__.py`
- `src/tradingbotsuite/v2/cli/main.py`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/autonomy_loop_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_autopilot_archive_cycle_phase75.py`
- `tests/v2/test_workers_phase7.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No provider/API download behavior except explicit rejection of unsafe
  `source=existing_ref` combinations.
- No strategy logic, validation scoring, ledger semantics, Lead Book scoring,
  or audit scoring changes.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_archive_cycle_phase75.py tests/v2/test_workers_phase7.py -q
```

Baseline:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Add `source=existing_ref` support to durable `universe_refresh` jobs so a
  planned cycle can verify an existing universe snapshot row and return
  `universe_snapshot_id` refs without writing universe data.
- Add `source=existing_ref` support to durable `recent_candle_bootstrap` jobs
  so a planned cycle can verify an existing silver archive snapshot and return
  `archive_snapshot_id` refs without writing market data.
- Add an `archive-cycle-spec` writer/CLI that generates the existing-ref
  bounded loop:
  `universe_refresh(existing_ref) -> recent_candle_bootstrap(existing_ref) ->
  coverage_audit -> strategy_queue_scan -> backtest_data_load ->
  vectorized_backtest -> validation_gate -> ledger_append_export ->
  lead_book_upsert -> audit_check`.
- Keep `accepted_research_ready=false` on plans/executions/reports. The cycle
  may finish with no blockers when the supplied archive refs, strategy spec,
  validation gate, ledger, Lead Book, and audit evidence all pass, but that is
  operational research evidence only.

## Acceptance Criteria

- Existing-ref universe and archive worker stages fail closed when refs are
  missing, malformed, or mismatched to requested context.
- Generated archive cycle specs contain no provider/API collection jobs and no
  fixture/public diagnostic blockers.
- Strategy specs are still accepted only through `strategy_queue_scan` and
  SHA-bound into vectorized backtests.
- Backtest-data refs are still loaded through `BacktestDataService` and bound
  into vectorized backtests with expected-ref verification.
- All outputs preserve canonical v2 research-only invariants and remain
  non-promotable, not candidate evidence, not candidate-pack eligible, not
  paper/live signals, not sizing/order instructions, and not runtime changes.

## Validation Evidence

Focused:

```text
python -m compileall -q src/tradingbotsuite: passed
PYTHONPATH=src python -m pytest tests/v2/test_autopilot_archive_cycle_phase75.py tests/v2/test_workers_phase7.py -q: 63 passed
archive-ref fixture cycle: completed with final audit status pass and no blockers
```

Baseline:

```text
python -m compileall -q src/tradingbotsuite: passed
PYTHONPATH=src python -m pytest tests/v2 -q: 548 passed
PYTHONPATH=src python -m pytest tests/contracts -q: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

`V2-AUD-COLLECT-021` is used for the collector portion because
`V2-AUD-COLLECT-017` already exists in the audit index.
