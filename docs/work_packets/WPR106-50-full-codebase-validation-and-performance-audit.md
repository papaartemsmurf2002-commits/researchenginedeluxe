# Work Packet: WPR106-50 full-codebase validation and performance audit

## Goal

Run a broad codebase validation and performance audit after WPR106-48 and
WPR106-49. Exercise all major modules with the full test suite, focused
high-risk suites, benchmark/performance tests, and selected diagnostic
performance commands. Fix only concrete regressions or unsafe behavior found
by the audit.

This packet is validation and hardening, not a candidate-readiness expansion.
It must not weaken research gates, emit candidate packs from blocked evidence,
or add live/paper execution behavior.

## Current Repo Facts

- Current implementation branch:
  `codex/wpr106-47-full-replay-exit-lab-controls`.
- WPR106-48 has uncommitted source/test/docs changes for first-class negative
  controls and bridge hardening.
- WPR106-49 added docs and local generated evidence only; no source changes
  were required for that packet.
- Generated WPR106-49 evidence removed missing replay-scope
  multiple-testing/validation-floor manifest blockers, but all 48 replay rows
  remain blocked and no candidate pack exists.
- `.pytest_cache` and older handoff prompt files are already dirty/untracked
  and unrelated to this packet.

## Allowed Edit Paths

This is a broad audit packet. Edits are allowed only when a validation or
performance audit finds a concrete issue:

- `docs/ACTIVE_INDEX.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_*.md`
- `docs/work_packets/WPR106-*.md`
- `docs/work_packets/WPR106-*-progress.jsonl`
- `src/tradingbot/**`
- `src/tradingbotsuite/**`
- `tests/**`
- `.github/workflows/**`
- `configs/**`
- `README.md`
- `pyproject.toml`

Generated empirical and performance artifacts under
`data/research/operator_runs/` are local research evidence outputs and remain
ignored by git.

## Research Boundary

- Research outputs are not live signals.
- Artifacts must remain `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.
- This packet must not add live signals, paper signals, order placement, sizing
  behavior, runtime-mode changes, live configuration writes, promotion-ready
  claims, candidate-ready claims, or candidate-pack writes.
- Performance measurements are diagnostic only unless a later scoped packet
  explicitly approves a speed claim with parity evidence.

## Audit Plan

1. Run full compile checks over active and legacy source plus tests.
2. Run full pytest with duration reporting.
3. Run grouped high-risk suites to isolate module-level failures:
   contracts, backtesting, features, historical, optimization,
   research_artifacts, research_discovery, live, and operator/tradingbot tests.
4. Run benchmark and performance-focused test modules.
5. Run selected local diagnostic performance commands where they are bounded and
   research-only.
6. Fix concrete failures if found and rerun the relevant suites.
7. Record command results, duration signals, residual warnings, and any
   blockers in a stage report.

## Acceptance Criteria

- Full compile passes for `src/tradingbot`, `src/tradingbotsuite`, and tests.
- Full pytest passes or any failure is fixed/documented with a blocking issue.
- High-risk grouped suites pass.
- Benchmark/performance-focused tests pass or are documented as unavailable for
  environment reasons.
- No candidate packs, live behavior, paper behavior, order placement, sizing,
  runtime-mode changes, live config writes, or promotion claims are introduced.

## Implementation Summary

- Fixed `write_research_experiment_benchmark_report()` so benchmark repeat
  specs are generated from a source-resolved `ResearchExperimentSpec` instead
  of copying raw relative paths into the benchmark output directory. This
  fixes checked repo configs such as
  `configs/experiments/v2_btc_phase1_research_experiment.json` when a separate
  benchmark output directory is supplied.
- Added a regression test proving repo-style relative `pipeline_spec` and
  `experiment_spec` paths are resolved before benchmark spec copying.
- Removed repeated pandas `FutureWarning`s from legacy
  `src/tradingbot/lorentz_lc.py` boolean shift handling by using a stable
  boolean-shift helper instead of object-typed `shift().fillna(False)`.
- Ran full, grouped, benchmark-focused, and CLI performance diagnostics. No
  candidate packs, live/paper behavior, order placement, sizing, runtime-mode
  change, live config write, or promotion claim was introduced.

## Performance Evidence

CLI benchmark artifacts were written under:

- `data/research/operator_runs/wpr106_50_full_codebase_validation_and_performance_audit/cli_benchmarks/`
- One early historical medium run resolved to
  `data/research/data/research/operator_runs/wpr106_50_full_codebase_validation_and_performance_audit/cli_benchmarks/historical_medium_repeat2/`
  because the command was intentionally given a `data/research/...` path before
  switching to cleaner `operator_runs/...` paths.

Results:

| Benchmark | Result |
| --- | --- |
| Historical cycle CLI, `medium`, repeat 2 | Gate passed, evidence complete, mean rows/sec 695.595861, mean candidate backtests/min 201.297838 |
| Discovery run CLI, `deep`, repeat 2 | Gate passed, evidence complete |
| Hardware utilization CLI, 16 workers, 5s CPU, 2s GPU, matrix 512 | CPU probe passed at 92.101484 percent worker/logical capacity; GPU probe executed with `cupy_matrix_probe_executed`; recommendation `hybrid_process_pool_cpu_plus_cuda_supported_fixed_holding` |
| Research experiment benchmark CLI, checked Phase 1 spec, repeat 1 | Passed after path-resolution fix; one run recorded |
| Historical cycle CLI, `provider_latest_month`, repeat 1, report-only | Completed; gate intentionally not passed because repeat 1 lacks determinism/cache-reuse evidence; mean rows/sec 2238.092193, mean candidate backtests/min 55.688712 |

Slowest test paths from the final full suite:

- `tests/historical/test_full_cycle_local_fixture_pack.py::test_checked_in_full_cycle_config_consumes_btcusdt_fixture_pack`: 123.81s.
- `tests/historical/test_full_cycle_local_fixture_pack.py::test_checked_in_eth_perp_context_v2_cycle_consumes_provider_context_fixture`: 67.45s.
- `tests/historical/test_full_cycle_local_fixture_pack.py::test_checked_in_perp_context_v2_cycle_consumes_provider_context_fixture`: 67.23s.
- `tests/historical/test_research_cycle_benchmark.py::test_research_cycle_benchmark_cleans_stale_repeat_artifacts`: 33.05s.
- `tests/tradingbotsuite/test_feature_ablation.py::test_stage12_feature_ablation_spec_executes_as_real_backtest`: 21.86s.

The only remaining final full-suite warning is an environment-level XGBoost
device fallback warning. The legacy pandas downcast warnings were removed.

## Validation Plan

Baseline:

```powershell
python -m compileall -q src\tradingbot src\tradingbotsuite tests
$env:PYTHONPATH='src'; python -m pytest -q --durations=30
```

Grouped suites:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\backtesting tests\features tests\historical tests\optimization tests\research_artifacts tests\research_discovery tests\live -q --durations=25
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite tests\unit -q --durations=25
```

Performance/benchmark focus:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_research_cycle_benchmark.py tests\backtesting\test_vector_engine_matches_reference.py tests\backtesting\test_cuda_batched_fixed_holding.py tests\optimization\test_gpu_screening.py -q --durations=25
```

Validation completed:

```powershell
python -m compileall -q src\tradingbot src\tradingbotsuite tests
python -m pip check
$env:PYTHONPATH='src'; python -m pytest -q --durations=30
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q --durations=20
$env:PYTHONPATH='src'; python -m pytest tests\backtesting tests\features tests\historical tests\optimization tests\research_artifacts tests\research_discovery tests\live -q --durations=30
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite tests\unit -q --durations=30
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_research_cycle_benchmark.py tests\research_cycle\test_hardware_utilization_benchmark.py tests\research_discovery\test_discovery_benchmark.py tests\backtesting\test_vector_engine_matches_reference.py tests\backtesting\test_cuda_batched_fixed_holding.py tests\optimization\test_gpu_screening.py -q --durations=30
$env:PYTHONPATH='src'; python -m pytest tests\integration -q --durations=20
$env:PYTHONPATH='src'; python -m pytest $(Get-ChildItem tests -File -Filter 'test_*.py' | ForEach-Object { $_.FullName }) -q --durations=30
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_experiment_runner.py -q --durations=20
$env:PYTHONPATH='src'; python -m pytest tests\test_strategy_flow.py tests\tradingbotsuite\test_hmm_knn.py -q --durations=20
git diff --check
```

Results:

- Final full suite after all patches: 1539 passed, 1 skipped, 1 warning in
  693.02 seconds.
- Full suite before warning cleanup: 1539 passed, 1 skipped, 92 warnings.
- Initial full suite before WPR106-50 fixes: 1538 passed, 1 skipped,
  92 warnings.
- Contracts: 441 passed.
- High-risk grouped suite: 554 passed, 1 skipped.
- Tradingbotsuite/unit grouped suite: 371 passed.
- Benchmark/vector/GPU-focused suite: 71 passed, 1 skipped.
- Integration suite: 20 passed.
- Top-level legacy tests: 142 passed.
- Experiment-runner focused suite: 15 passed.
- Strategy-flow/HMM focused suite: 43 passed.
- `python -m pip check`: no broken requirements found.
- `git diff --check`: passed with line-ending warnings only.
