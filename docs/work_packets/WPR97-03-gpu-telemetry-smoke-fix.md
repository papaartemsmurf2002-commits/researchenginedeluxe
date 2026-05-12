# WPR97-03 GPU Telemetry Smoke Fix

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Fix issues found during the R97 post-push GPU performance/correctness smoke.

The default GPU mini full-cycle smoke correctly used
`cuda_batched_fixed_holding` for aggregate screening and CPU/reference for
validation, with CUDA manifest parity passing. However, the cycle-level
stability acceleration counters still reported `parity_rechecked_count: 0`
because the backtest index did not carry the CUDA backend's exact parity status.

## Allowed Paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/**`
- `docs/work_packets/**`
- `src/tradingbotsuite/research_cycle/**`
- `tests/contracts/**`
- `tests/historical/**`

## Scope

- Carry CUDA exact parity status and max-diff evidence into backtest index
  backend evidence.
- Count CUDA aggregate parity rechecks and mismatches in research-cycle
  stability acceleration counters.
- Add focused test coverage for the default GPU telemetry.

## Non-Goals

- No live trading behavior, live config, order placement, promotion readiness,
  or sizing changes.
- No GPU speedup claim.

## Validation Result

Passed on 2026-05-12:

- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_synthetic.py -q`
  - `17 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py -q`
  - `47 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_research_cycle_benchmark.py tests\historical\test_full_cycle_local_fixture_pack.py -q`
  - `23 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_cuda_batched_fixed_holding.py tests\optimization\test_gpu_screening.py -q`
  - `11 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
  - `152 passed`
- Mini default GPU full-cycle smoke on RTX 5070 Ti
  - Aggregate backend `cuda_batched_fixed_holding`
  - Aggregate parity `passed`
  - `parity_rechecked_count: 4`
  - `mismatch_count: 0`

Stage report:
`docs/stage_reports/STAGE_R97_GPU_TELEMETRY_SMOKE_FIX_REPORT.md`
