# WPR106-428 - V2 Durable Vectorized Backtest Worker

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-WORKER-006`
- `V2-AUD-BTENG-006`
- `V2-AUD-BTDATA-004`
- `V2-AUD-STRAT-006`

## Purpose

Wire archive-backed vectorized backtests into the durable worker runner so long
backtest jobs do not run as ephemeral in-process helper calls. This packet does
not change the v2 strategy language, backtest-data policy floors, cost model,
ledger, Lead Book, event-driven semantics, UI, or any paper/live/order/sizing
runtime boundary.

## Allowed Paths

- `docs/work_packets/WPR106-428-v2-durable-vectorized-backtest-worker.md`
- `docs/contracts/worker_job_contract.md`
- `docs/contracts/backtest_engine_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/backtest_engine/jobs.py`
- `src/tradingbotsuite/v2/backtest_engine/__init__.py`
- `src/tradingbotsuite/v2/workers/runner.py`
- `tests/v2/test_workers_phase7.py`

## No-Touch Paths

No no-touch path is in scope. This packet must not modify live/runtime/order
placement/sizing/promotion paths, candidate-pack truth-layer paths, generated
research evidence, legacy GUI paths, old `tradingbot` compatibility code,
secrets, or local state.

## Decisions Made

- Implement `vectorized_backtest` as the first durable long-backtest worker
  lane. `backtest` may dispatch to the same vectorized handler only when the
  input spec does not request another engine lane.
- Accept inline declarative `strategy_spec` payloads only in this packet.
  Strategy-spec file intake is deliberately deferred so no new trusted-file
  boundary or secret-scan policy is introduced here.
- Load panels only through `BacktestDataService`, preserving the existing
  2024+, six-month, 0.98 coverage, as-of universe, and lockbox gates before
  strategy code sees rows.
- Treat engine-level failed run manifests as useful research artifacts and
  successful worker execution, while data/spec/preflight failures remain worker
  failures with retry/terminal handling from the job store.

## Expected Tests

- Focused:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py tests/v2/test_backtest_data_phase9.py tests/v2/test_backtest_engine_phase11.py tests/v2/test_strategy_specs_phase10.py -q`
- Broad v2:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
- Baseline:
  - `python -m compileall -q src/tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- Hygiene:
  - `git diff --check`

## Changed Files

- `docs/work_packets/WPR106-428-v2-durable-vectorized-backtest-worker.md`
- `docs/contracts/worker_job_contract.md`
- `docs/contracts/backtest_engine_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/backtest_engine/jobs.py`
- `src/tradingbotsuite/v2/backtest_engine/__init__.py`
- `src/tradingbotsuite/v2/workers/runner.py`
- `tests/v2/test_workers_phase7.py`

## Acceptance Evidence

- Focused worker smoke:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py -q`
  - Result: `20 passed`
- Focused worker/data/spec/engine lane:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py tests/v2/test_backtest_data_phase9.py tests/v2/test_backtest_engine_phase11.py tests/v2/test_strategy_specs_phase10.py -q`
  - Result: `48 passed`
- Broad v2:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  - Result: `198 passed`
- Baseline compile:
  - `python -m compileall -q src/tradingbotsuite`
  - Result: passed
- Contract baseline:
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  - Result: `463 passed`
- Diff hygiene:
  - `git diff --check`
  - Result: passed with existing LF-to-CRLF working-copy warnings only

## Boundary Statement

The packet remains research-only and observe-only. It must not create accepted
evidence by itself, autonomous-ready status, candidate-pack eligibility,
paper/live/order/sizing/runtime behavior, or promotion readiness.
