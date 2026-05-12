# Stage R97 GPU Telemetry Smoke Fix Report

Date: 2026-05-12
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR97-03-gpu-telemetry-smoke-fix.md`

## Summary

Post-push GPU verification found one telemetry defect: CUDA batched aggregate
manifests recorded `parity_status: passed`, but the research-cycle
stability acceleration counters still reported `parity_rechecked_count: 0`.

The fix carries exact CUDA parity status and max-diff fields into the
backtest index and counts aggregate CUDA parity rechecks/mismatches from that
evidence.

## Performance Estimate

Local RTX 5070 Ti measurements on warm deterministic single-candidate
artifact-producing runs do not support a speedup claim for the current exact
backtest lane:

- 720 rows: CUDA batched median was about `1 / 0.68 = 1.47x` slower than reference and `1 / 0.618 = 1.62x` slower than vector.
- 2880 rows: CUDA batched median was about `1 / 0.834 = 1.20x` slower than reference and `1 / 0.659 = 1.52x` slower than vector.
- 5760 rows: CUDA batched median was about `1 / 0.865 = 1.16x` slower than reference and `1 / 0.726 = 1.38x` slower than vector.

This is expected for the current implementation shape: pandas signal
generation, full CPU parity, CPU trade assembly, and artifact writes dominate
single-candidate wall time. The code correctly keeps `speed_claimed: false`.

The practical improvement from R97 is capability and evidence, not a measured
single-candidate speedup yet: default GPU screening now executes with exact
parity evidence, and unsupported/unavailable paths fall back to CPU/reference.

## Correctness Smoke

Mini default full-cycle GPU smoke on RTX 5070 Ti:

- Default requested backend: `auto`
- Default profile: `cuda_exact_batched`
- Aggregate backend: `cuda_batched_fixed_holding`
- Validation backend: `reference`
- Aggregate parity status: `passed`
- Max metric/equity/trade diff: `0.0`
- `parity_rechecked_count`: `4`
- `mismatch_count`: `0`
- Research boundary flags stayed true/false as required.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_synthetic.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_research_cycle_benchmark.py tests\historical\test_full_cycle_local_fixture_pack.py -q
$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_cuda_batched_fixed_holding.py tests\optimization\test_gpu_screening.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
```

Observed results:

- `tests/historical/test_full_cycle_synthetic.py`: `17 passed`
- `tests/contracts/test_research_cycle_contract.py`: `47 passed`
- benchmark + local fixture historical tests: `23 passed`
- CUDA batched + GPU screening tests: `11 passed`
- `tests/research_discovery`: `152 passed`

## Boundary

No live trading behavior, live config, order placement, promotion readiness, or
sizing logic was changed. No speedup claim was added.
