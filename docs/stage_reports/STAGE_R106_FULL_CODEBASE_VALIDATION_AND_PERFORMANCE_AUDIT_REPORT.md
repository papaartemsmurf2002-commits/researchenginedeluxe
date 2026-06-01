# Stage R106 Full-Codebase Validation And Performance Audit Report

Work packet:
`docs/work_packets/WPR106-50-full-codebase-validation-and-performance-audit.md`

Date: 2026-05-31

## Summary

WPR106-50 ran a broad validation and diagnostic performance audit across the
codebase after WPR106-48 and WPR106-49. The audit found and fixed one real CLI
benchmark path-resolution bug and cleaned up repeated pandas FutureWarnings in
the legacy Lorentzian strategy flow.

No research gate was weakened. No candidate pack was written. No live/paper
behavior, order placement, sizing, runtime-mode change, live config write, or
promotion claim was introduced.

## Code Changes

`src/tradingbotsuite/research/experiment_runner.py`:

- `write_research_experiment_benchmark_report()` now resolves the source
  `ResearchExperimentSpec` before writing per-repeat benchmark specs.
- This preserves repo-config-relative `pipeline_spec` and `experiment_spec`
  paths when benchmark outputs are written elsewhere.
- The benchmark report now records `resolved_source_spec` for auditability.

`tests/tradingbotsuite/test_experiment_runner.py`:

- Added a regression test for repo-style relative child specs copied into a
  separate benchmark output directory.

`src/tradingbot/lorentz_lc.py`:

- Added stable boolean-shift handling for legacy signal/exit logic.
- Removed repeated pandas downcast `FutureWarning`s from
  `shift().fillna(False)` without changing signal semantics.

## Validation

Final validation after all patches:

```powershell
python -m compileall -q src\tradingbot src\tradingbotsuite tests
python -m pip check
$env:PYTHONPATH='src'; python -m pytest -q --durations=30
git diff --check
```

Results:

- Final full suite: 1539 passed, 1 skipped, 1 warning in 693.02 seconds.
- `python -m pip check`: no broken requirements found.
- Compileall passed.
- `git diff --check` passed with line-ending warnings only.

Additional grouped validation:

- Contracts: 441 passed.
- High-risk grouped suite
  (`backtesting`, `features`, `historical`, `optimization`,
  `research_artifacts`, `research_discovery`, `live`): 554 passed, 1 skipped.
- `tests/tradingbotsuite tests/unit`: 371 passed.
- Benchmark/vector/GPU-focused suite: 71 passed, 1 skipped.
- Integration suite: 20 passed.
- Top-level legacy tests: 142 passed.
- Experiment-runner focused suite: 15 passed.
- Strategy-flow/HMM focused suite: 43 passed.

The repeated legacy pandas warnings were removed. The single remaining warning
is an environment-level XGBoost device fallback warning during the data-pipeline
test.

## Performance Evidence

CLI benchmark artifacts:

- Historical medium repeat 2:
  `data/research/data/research/operator_runs/wpr106_50_full_codebase_validation_and_performance_audit/cli_benchmarks/historical_medium_repeat2/research_cycle_benchmark_report.json`
- Discovery deep repeat 2:
  `data/research/operator_runs/wpr106_50_full_codebase_validation_and_performance_audit/cli_benchmarks/discovery_deep_repeat2/discovery_benchmark_report.json`
- Hardware utilization:
  `data/research/operator_runs/wpr106_50_full_codebase_validation_and_performance_audit/cli_benchmarks/hardware_16w_gpu2s/hardware_utilization_report.json`
- Research experiment benchmark:
  `data/research/operator_runs/wpr106_50_full_codebase_validation_and_performance_audit/cli_benchmarks/research_experiment_phase1_repeat1/benchmark_report.json`
- Historical provider latest-month report-only:
  `data/research/operator_runs/wpr106_50_full_codebase_validation_and_performance_audit/cli_benchmarks/historical_provider_latest_month_repeat1/research_cycle_benchmark_report.json`

Observed results:

- Historical `medium`, repeat 2: gate passed, evidence complete, mean
  rows/sec 695.595861, mean candidate backtests/min 201.297838.
- Discovery `deep`, repeat 2: gate passed and evidence complete.
- Hardware probe: CPU probe succeeded at 92.101484 percent worker/logical
  capacity; GPU probe succeeded with `cupy_matrix_probe_executed`; best option
  `hybrid_process_pool_cpu_plus_cuda_supported_fixed_holding`.
- Research experiment benchmark: checked Phase 1 config succeeds after the
  path-resolution fix.
- Historical `provider_latest_month`, repeat 1: completed as report-only
  evidence; gate did not pass because repeat 1 intentionally lacks
  determinism/cache-reuse evidence. No threshold failure was reported.

Slowest final full-suite tests:

- BTC checked full-cycle fixture pack: 123.81s.
- ETH perp-context fixture full cycle: 67.45s.
- BTC perp-context fixture full cycle: 67.23s.
- Research-cycle stale-repeat benchmark: 33.05s.
- Stage 12 feature-ablation real backtest: 21.86s.

## Research Boundary

- Research outputs are not live signals.
- Benchmark outputs are diagnostic research evidence only.
- No speedup claim, candidate-ready claim, paper-ready claim, live-ready claim,
  or promotion-ready claim is made.
- Candidate-pack, live, paper, order-placement, sizing, runtime-mode, and live
  configuration behavior were not changed.

## Issue State

No new P0 or P1 issue was opened. The benchmark path-resolution bug was fixed
inside this packet and covered by regression tests. `ISSUE-R104-001` remains
open because this validation packet does not provide passing candidate evidence
or eligible candidate-pack rows.
