# WPR96-01 CUDA Fixed-Holding Parity And Stability Search

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Implement the first research-only GPU acceleration layer for RTX 50-series /
Blackwell systems without changing live behavior or overstating evidence. The
initial backend is limited to fixed-holding primary-bar backtests with parity
contracts and conservative CPU fallback.

## Allowed Paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/**`
- `docs/work_packets/**`
- `src/tradingbotsuite/backtesting/**`
- `src/tradingbotsuite/optimization/**`
- `src/tradingbotsuite/research_cycle/**`
- `tests/backtesting/**`
- `tests/contracts/test_backtest_contracts.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `tests/historical/test_research_cycle_benchmark.py`
- `tests/optimization/**`
- `tests/live/test_preflight.py`

## Scope

- Add optional `cuda_fixed_holding` backtest backend with lazy CuPy import.
- Keep backend scope identical to current CPU vector fixed-holding support.
- Add GPU availability/support reason codes and truthful manifest/backend
  evidence.
- Route `auto` to CUDA only when compute policy requests GPU and the candidate
  is backend-eligible; otherwise preserve existing CPU vector/reference paths.
- Add parity and fallback tests, including skip-safe GPU execution tests.
- Extend candidate-selection performance artifacts with stability-region
  acceleration counters.

## Non-Goals

- No live-ready candidate declaration, live config writes, order placement,
  runtime mode changes, or sizing logic.
- No CUDA acceleration claims without backend evidence.
- No rich-exit, lower-timeframe, KNN, or Tensor Core/FP4/FP8 acceleration.
- No exhaustive brute-force run.

## Validation Plan

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\backtesting -q
$env:PYTHONPATH='src'; python -m pytest tests\optimization -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_backtest_contracts.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_synthetic.py -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_research_cycle_benchmark.py -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q
git diff --check
```

## Validation Result

Passed:

- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_vector_engine_matches_reference.py -q` (`31 passed, 1 skipped`)
- `$env:PYTHONPATH='src'; python -m pytest tests\optimization\test_stability_region_search_controller.py -q` (`3 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py -q` (`36 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_synthetic.py -q` (`15 passed, 1 skipped`)
- `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py -q` (`11 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_research_cycle_benchmark.py -q` (`12 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests\optimization -q` (`23 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests\backtesting -q` (`90 passed, 1 skipped`)
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` (`402 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q` (`152 passed`)
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` (`32 passed`)
- `git diff --check` (passed)

## Exit Evidence

- Stage report:
  `docs/stage_reports/STAGE_R96_GPU_ACCELERATED_STABILITY_REGION_SEARCH_REPORT.md`
- `ISSUE-R95-001` resolved in `docs/KNOWN_ISSUES.md`.
- CUDA remains diagnostic-only with `speed_claimed: false`; split/cost-stress
  validation is forced back to CPU/reference when GPU routing is requested.
- No live config, runtime mode, order placement, promotion readiness, or sizing
  logic changed.
