# Stage R105 Blocked Artifact Directory Suppression Report

Date: 2026-05-19
Owner: Codex Research Agent
Stage: R105 candidate factory component falsification
Status: filesystem-pressure reduction complete; execution semantics unchanged

## Research Boundary

This packet changes only real-discovery artifact directory materialization. It
does not change discovery scoring, HMM/KNN behavior, candidate gates, ledgers,
trial JSON records, live execution, runtime mode, order placement, live
configuration, promotion behavior, or sizing behavior.

## Implemented

`src/tradingbotsuite/research_discovery/runner.py` no longer eagerly creates
`trial_artifacts/<trial_id>/<attempt_id>` before a real-discovery trial is
evaluated. Artifact writers still create their parent directories when HMM,
KNN, or strategy-accounting artifacts are actually persisted.

For blocked `interesting_only` trials, the durable JSON trial record remains
under `trials/`, but no empty `trial_artifacts` root is left behind.

## Performance Scope

This is a filesystem-pressure cleanup, not a processor-parallelism fix. It is
useful for no-candidate exact sweeps like R104 because blocked trials do not
need empty artifact directories. CPU underutilization remains visible through
WPR105-03 telemetry and should be addressed by a later scheduler/effective-work
packet.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_runner.py::test_discovery_runner_compacts_blocked_real_trial_artifacts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONDONTWRITEBYTECODE='1'; $env:PYTHONPATH='src'; python -m pytest -q -p no:cacheprovider tests\research_discovery\test_compute_telemetry.py tests\research_discovery\test_discovery_runner.py::test_discovery_runner_writes_manifest_state_ledgers_and_snapshots tests\research_discovery\test_discovery_runner.py::test_discovery_runner_compacts_blocked_real_trial_artifacts tests\research_discovery\test_discovery_benchmark.py::test_discovery_benchmark_report_contains_research_only_gate_metrics tests\historical\test_full_cycle_synthetic.py::test_cycle_auto_backend_default_uses_fastest_exact_vector_route tests\historical\test_full_cycle_synthetic.py::test_full_cycle_expands_optimizer_search_spaces_and_writes_stability_regions tests\historical\test_research_cycle_benchmark.py::test_research_cycle_benchmark_report_contains_research_only_gate_metrics
git diff --check
```

Results:

- focused blocked-artifact regression: `1 passed`
- `tests/research_discovery`: `180 passed`
- `tests/contracts`: `427 passed`
- targeted performance-surface validation: `7 passed`
- `git diff --check`: passed with CRLF normalization warnings only
