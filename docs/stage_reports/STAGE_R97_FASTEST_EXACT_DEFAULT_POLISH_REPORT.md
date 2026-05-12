# Stage R97 Fastest Exact Default Polish Report

Date: 2026-05-12
Work packet: `docs/work_packets/WPR97-05-fastest-exact-default-polish.md`

## Summary

WPR97-05 finishes the R97 runtime default polish. The default historical-cycle
compute policy now explicitly selects the fastest parity-safe route currently
available in the repo:

- `compute.gpu_execution_profile: fastest_exact`
- `compute.cpu_threads: 15`
- `backtest_backend: auto`
- aggregate fixed-holding screening: `vector_fixed_holding` when supported
- validation backtests: `reference` under `auto_validation_reference_required`
- explicit CUDA evidence modes remain opt-in

This keeps the branch fast by default without pretending the current
one-candidate CUDA backend is faster than measured. CUDA/Tensor Core paths stay
available for diagnostic evidence through explicit `cuda_exact_batched` or
`hybrid_tensorcore_screening`.

Update: WPR97-07 supersedes the worker count after higher-worker testing. The
current default is `compute.cpu_threads: 48`.

## Behavior Changes

- Added accepted compute profile `fastest_exact`.
- Made `fastest_exact` the default profile.
- Made 15 CPU aggregate workers the default.
- Kept `conservative` as a backward-compatible CPU/vector route.
- Added distinct fallback/performance evidence:
  `gpu_execution_profile_fastest_exact_vector_selected`.
- Added `cuda_runtime_checked` in the performance plan so default CPU/vector
  routing does not look like a failed CUDA runtime probe.
- Updated GPU truthfulness text to state that the default fastest route does not
  select CUDA unless GPU profiles are requested.

## Default Smoke

Synthetic full-cycle default specs with no explicit `compute` block:

| Rows | Median seconds | Aggregate backend | Validation backend | Workers |
| ---: | ---: | --- | --- | ---: |
| 240 | 5.092 | `vector_fixed_holding` | `reference` | 15 |
| 720 | 8.723 | `vector_fixed_holding` | `reference` | 15 |

Observed default compute evidence:

- `gpu_execution_profile: fastest_exact`
- `gpu_execution_status: gpu_execution_profile_fastest_exact_vector_selected`
- `selected_cuda_backend: ""`
- `cuda_runtime_checked: false`
- `r97_batched_cuda_requested: false`

## Boundaries

All behavior remains research-only:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- no live config changes
- no order placement
- no sizing behavior changes

The default route is a throughput default, not a live-readiness or promotion
claim. Candidate readiness remains blocked by the existing reference validation,
exit-lab, comparator, no-regime baseline, validation-floor, and evidence gates.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_synthetic.py -q
```

Additional default full-cycle smoke was run for 240-row and 720-row synthetic
specs without explicit compute overrides.
