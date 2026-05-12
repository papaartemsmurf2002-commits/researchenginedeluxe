# WPR97-01 Aggressive CUDA TensorCore Stability Search

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Extend the R96 research-only CUDA foundation with a more aggressive, still
truthful acceleration layer:

- an exact batched CUDA fixed-holding backend for parity-testable screening,
- a Tensor Core screening surface for matrix-heavy diagnostics only,
- stability-region counters and routing evidence that distinguish GPU exact
  screening, Tensor Core prefilters, and CPU/reference validation.

This packet is a research throughput packet. It does not make any candidate
live-ready and does not change live trading behavior.

## Allowed Paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/**`
- `docs/work_packets/**`
- `src/tradingbotsuite/backtesting/**`
- `src/tradingbotsuite/optimization/**`
- `src/tradingbotsuite/research_cycle/**`
- `tests/backtesting/**`
- `tests/contracts/**`
- `tests/historical/**`
- `tests/optimization/**`

## Scope

- Add `cuda_batched_fixed_holding` as an explicit historical-cycle backtest
  backend.
- Preserve existing `cuda_fixed_holding` as the R96 diagnostic backend.
- Add backward-compatible compute spec fields for GPU execution profile, Tensor
  Core screening policy, GPU batch size, memory limit, and validation sample
  rate.
- Add CUDA backend evidence fields for RawKernel scope, kernel hash, detected
  SM target, precision and determinism policies, parity status, CPU reference
  hash, max diffs, and fallback reason.
- Add a separate `cuda_screening_batch_v1` optimization/Tensor Core screening
  module that can rank matrix-heavy diagnostic workloads but cannot satisfy
  candidate gates or final validation.
- Extend stability-region acceleration counters to distinguish Tensor Core
  screened, GPU exact screened, CPU/reference validated, parity rechecked, and
  mismatch counts.
- Add focused tests for routing, fallback, manifest evidence, parity, Tensor
  Core diagnostic boundaries, and stability counters.

## Non-Goals

- No live config writes, order placement, runtime mode changes, promotion
  readiness, or sizing changes.
- No Tensor Core use for final trade accounting, event counting, costs, or
  candidate acceptance.
- No rich-exit, lower-timeframe, true L2/depth, liquidation, or KNN acceptance
  acceleration beyond diagnostic screening evidence.
- No speedup claim unless parity evidence and benchmark evidence explicitly
  support it.

## Validation Plan

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\backtesting -q
$env:PYTHONPATH='src'; python -m pytest tests\optimization -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_research_cycle_benchmark.py -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_synthetic.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
git diff --check
```

## Validation Result

Passed on 2026-05-12:

- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `413 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\backtesting tests\optimization tests\historical\test_research_cycle_benchmark.py tests\historical\test_full_cycle_synthetic.py -q`
  - `156 passed, 1 skipped`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
  - `152 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_cuda_batched_fixed_holding.py::test_cuda_batched_fixed_holding_matches_reference_when_runtime_available -q`
  - `1 passed`
- `git diff --check`

## Exit Evidence

Stage report:
`docs/stage_reports/STAGE_R97_AGGRESSIVE_CUDA_TENSORCORE_STABILITY_SEARCH_REPORT.md`
