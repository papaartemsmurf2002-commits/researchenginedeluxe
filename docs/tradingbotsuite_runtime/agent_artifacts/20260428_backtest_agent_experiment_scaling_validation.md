# Agent name

Backtest Agent

# Task received

Improve the HMM/KNN experiment runner and backtest scaling path. Add bounded parallel workers for independent experiment specs if the runner is sequential, keep deterministic artifact paths and cache keys stable, add summary fields for runtime, cache hit status, artifact manifest paths, and promotion failure aggregation, and add deterministic/no-network tests. Do not touch live execution, operator UI, Hyperliquid, sizing, or runtime control files.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_RUNBOOK.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_next_experiment_matrix.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_experiment_runner_manifest_caching.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_deterministic_sweep_datasets.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_experiment_performance_report.md`
- `src/tradingbotsuite/research/hmm_knn_experiments.py`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/deterministic_datasets.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `configs/experiments/v2_btc_hmm_knn_deterministic_sweep_experiments.json`

# Files changed

- `src/tradingbotsuite/research/hmm_knn_experiments.py`
- `src/tradingbotsuite/main.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_experiment_scaling_validation.md`

Concurrent worktree changes by other agents were present after validation and were not reverted or edited by this task:

- `configs/v2_btc_hmm_multi_knn_research.json`
- `src/tradingbotsuite/research/hmm_knn.py`
- `src/tradingbotsuite/research/hmm_knn_experiments.py` also contained concurrent research-boundary validation additions; this task kept them and layered the worker/runtime/cache summary changes on top.
- `src/tradingbotsuite/research/hmm_knn_monitoring.py`
- `src/tradingbotsuite/research/live_readiness.py`
- `tests/tradingbotsuite/test_live_readiness.py`
- `src/tradingbotsuite/research/market_journal.py`
- `tests/tradingbotsuite/test_market_journal.py`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_gpu_lorentzian_backend.md`

# Commands/tests run

```powershell
git status --short --branch
git rev-parse --short HEAD
Get-Content -Path docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md
Get-Content -Path docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md
Get-Content -Path docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md
Get-Content -Path docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md
Get-Content -Path docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_RUNBOOK.md
rg -n "experiment|sweep|runner|cache|promotion_fail|runtime_seconds|cache_hit" src tests docs/tradingbotsuite_runtime -g "*.py" -g "*.md" -g "*.json"
Get-Content -Path src/tradingbotsuite/research/hmm_knn_experiments.py
Get-Content -Path configs/experiments/v2_btc_hmm_knn_deterministic_sweep_experiments.json
Get-Content -Path docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_next_experiment_matrix.md
Get-Content -Path docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_experiment_runner_manifest_caching.md
Get-Content -Path docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_deterministic_sweep_datasets.md
Get-Content -Path docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_experiment_performance_report.md
```

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py::test_hmm_knn_experiment_runner_writes_manifest_summary_and_monitoring tests/tradingbotsuite/test_hmm_knn.py::test_hmm_knn_experiment_runner_reuses_complete_cached_artifact tests/tradingbotsuite/test_hmm_knn.py::test_hmm_knn_experiment_runner_parallel_workers_preserve_order_and_cache_keys tests/tradingbotsuite/test_hmm_knn.py::test_hmm_knn_experiment_runner_accepts_utf8_sig_specs -q
```

Result: `4 passed in 5.03s`.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
```

Result: `35 passed in 15.86s`.

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main run-hmm-knn-experiments --help
```

Result: help output includes `--workers WORKERS`.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py tests/tradingbotsuite/test_hmm_knn.py -q
```

Result: `53 passed in 17.41s`.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_live_readiness.py tests/tradingbotsuite/test_hmm_knn.py -q
```

Result: `42 passed in 14.67s`.

```powershell
git diff --check
```

Result: exit code `0`; line-ending warnings only.

# Decisions made

- Added `max_workers` to `run_hmm_knn_experiment_matrix()` and `--workers` to the CLI.
- Default behavior remains sequential with `max_workers=1`.
- `--fail-fast` keeps effective execution sequential because true fail-fast semantics are not meaningful once multiple independent experiments are already running.
- Prepared all per-experiment config files and cache keys before execution. Cache identity remains unchanged: runner version, dataset hash, and final config payload hash.
- Parallel execution uses `ThreadPoolExecutor` with `effective_workers = min(max_workers, experiment_count)`.
- Collected and sorted records by `run_order` before writing `experiment_manifest.json` and `experiment_summary.csv`, so output order stays deterministic even when worker completion order differs.
- Added per-experiment fields: `runtime_seconds`, `cache_hit`, `artifact_manifest`, `artifact_manifest_path`, and `promotion_failures`.
- Added top-level fields: `runtime_seconds`, `max_workers`, `effective_workers`, and `promotion_failure_counts`.
- Added a deterministic-sweep fixture test that runs two independent experiment specs with `max_workers=2`, checks ordered summaries, verifies first-run cache misses, verifies second-run cache hits, and confirms cache keys/artifact paths remain stable.

# Assumptions

- Independent experiment specs may run concurrently when they have distinct final config payloads and cache keys.
- The runner remains a research-only orchestration surface. It does not create live signals, live gates, live sizing, operator controls, Hyperliquid orders, or runtime safety state.
- Runtime timings are intentionally reported as diagnostics and are not part of deterministic cache identity.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` showed no open issues when checked. No blocker artifact or issue append was needed.

# Handoff notes for other agents

- Use `--workers N` for local HMM/KNN matrix plumbing when experiment specs are independent. Keep `N` modest because each worker may run a full HMM/KNN research job.
- Cache keys and artifact paths should remain stable across sequential and parallel runs for the same dataset and final config payload.
- Monitoring can aggregate `promotion_failure_counts` from `experiment_manifest.json` and per-run `promotion_failures` from `experiment_summary.csv`.
- Execution/Risk should continue treating the experiment runner as offline research only and non-promotional.
