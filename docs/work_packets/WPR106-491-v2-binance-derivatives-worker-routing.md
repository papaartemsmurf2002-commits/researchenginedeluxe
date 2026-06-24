# WPR106-491 - V2 Binance Derivatives Worker Routing

Status: closed
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-019`
- `V2-AUD-WORKER-026`
- `V2-AUD-COLLECT-019`

## Objective

Complete the `DATA-006` operational handoff by routing the local Binance USD-M
derivatives context backfill chain through durable worker execution. The worker
kind must run a bounded single family/symbol job, preserve blocked coverage as
successful blocker evidence, and support offline fixture payloads for tests.

This packet does not run unattended broad backfills, schedule recurring jobs,
run backtests, create accepted Hyperliquid-native evidence, create candidate
evidence, create candidate packs, add paper/live behavior, place orders, emit
sizing instructions, change runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-491-v2-binance-derivatives-worker-routing.md`
- `docs/contracts/worker_job_contract.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/workers/**`
- `src/tradingbotsuite/v2/collectors/**`
- `tests/v2/test_binance_derivatives_worker_phase54.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No legacy GUI paths.
- No checked legacy evidence under `data/research/fixtures/**`,
  `data/research/historical_cycles/**`, or existing WPR evidence directories.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_worker_phase54.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Add `binance_derivatives_context_backfill` as a durable collector worker
  kind.
- Route through `run_binance_derivatives_context_backfill()`.
- Support `source=fixture_payloads` for offline deterministic worker tests and
  `source=public_api` for operator-invoked public REST mode.
- Return succeeded worker status for completed and blocked research evidence;
  invalid specs remain worker failures through existing runner behavior.

## Acceptance Criteria

- A fixture-backed funding context worker job writes archive/coverage refs and
  succeeds with accepted external-comparison coverage refs.
- A fixture-backed current-OI job succeeds with explicit blocked coverage refs.
- Worker output refs expose page, archive-ingest, coverage, acceptance, and
  blocker metadata while preserving research-only boundaries.

## Changed Files

- `src/tradingbotsuite/v2/workers/models.py`
- `src/tradingbotsuite/v2/workers/runner.py`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_binance_derivatives_worker_phase54.py`
- `docs/contracts/worker_job_contract.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`

## Validation Evidence

```text
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
passed

$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_worker_phase54.py -q
3 passed

$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
409 passed

$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
463 passed

git diff --check
passed with existing LF-to-CRLF warnings only
```

## Closeout Notes

WPR106-491 completes the bounded durable worker handoff for the local
single-family Binance USD-M derivatives context backfill chain. The worker
returns page, archive-ingest, coverage-report, acceptance, source-mode, and
blocker refs for completed and blocked evidence. It does not add broad
unattended scheduling, Hyperliquid-native evidence, backtests, accepted
research evidence by itself, candidate packs, paper/live behavior, order
placement, sizing, runtime-mode changes, or promotion claims.
