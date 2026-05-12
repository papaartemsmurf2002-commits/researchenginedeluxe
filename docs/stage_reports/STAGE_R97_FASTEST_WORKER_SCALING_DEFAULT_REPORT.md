# Stage R97 Fastest Worker Scaling Default Report

Date: 2026-05-12
Work packet: `docs/work_packets/WPR97-07-fastest-worker-scaling-default.md`

## Summary

WPR97-07 tested higher aggregate worker counts for the `fastest_exact`
research-cycle route and updates the default from 15 workers to 48 workers.

This remains a research-only throughput default:

- aggregate screening: `vector_fixed_holding`
- validation: `reference`
- GPU/Tensor Core: explicit diagnostic paths only
- no live, promotion, order-placement, or sizing behavior changes

## Worker Test

Synthetic 720-row full-cycle benchmark, three repeats per worker count:

| Workers | Median s | Min s | Max s | Assigned | Aggregate backend | Validation backend |
| ---: | ---: | ---: | ---: | --- | --- | --- |
| 15 | 8.560 | 8.541 | 8.672 | yes | `vector_fixed_holding` | `reference` |
| 24 | 8.518 | 8.421 | 8.686 | yes | `vector_fixed_holding` | `reference` |
| 32 | 8.490 | 8.466 | 8.620 | yes | `vector_fixed_holding` | `reference` |
| 48 | 8.474 | 8.453 | 8.512 | yes | `vector_fixed_holding` | `reference` |
| 64 | 8.605 | 8.570 | 8.647 | yes | `vector_fixed_holding` | `reference` |

48 workers was the fastest reliable median. 64 workers was assigned correctly
but slower, so the default is not set to the maximum.

The run used 44 aggregate candidate backtests, so possible active aggregate
workers were capped at 44 for the 48-worker and 64-worker specs.

## Behavior Changes

- `CycleComputeSpec.cpu_threads` default is now 48.
- Historical benchmark backend comparison labels and evidence now use CPU48
  naming instead of CPU15.
- Contract and historical tests now assert 48-worker default evidence.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\historical\test_full_cycle_synthetic.py tests\historical\test_research_cycle_benchmark.py tests\tradingbotsuite\test_operator_ui.py::test_operator_artifacts_include_historical_cycle_profitability_summary -q
```

Result: `79 passed`.
