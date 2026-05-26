# WPR105-03 Discovery Processor Utilization Telemetry

Owner: Codex Research Agent
Stage: R105 candidate factory component falsification
Status: closed
Created: 2026-05-19

## Goal

Address the reported processor-utilization concern by making discovery run
manifests show CPU usage relative to both logical processor capacity and active
worker capacity. The current telemetry records wall time, process CPU seconds,
and active workers, but it does not normalize CPU consumption in a way that
operators can use to distinguish CPU-bound work from I/O, scheduler, artifact,
or cache-bound work. This packet also makes parent-runner artifact write time
observable for future discovery manifests.

## Allowed paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/**`
- `docs/stage_reports/**`
- `src/tradingbotsuite/research_discovery/runner.py`
- `src/tradingbotsuite/research_discovery/telemetry.py`
- `tests/research_discovery/**`
- `tests/contracts/**`

## Constraints

- Telemetry-only; do not change discovery scoring, KNN behavior, search-space
  generation, candidate-pack gates, live execution, runtime mode, order
  placement, live config, promotion behavior, or sizing behavior.
- Keep outputs research-only, observe-only, and `promotion_ready: false`.
- Preserve backwards-compatible raw process CPU fields while adding normalized
  utilization fields.
- Do not claim a speedup unless measured by a benchmark.

## Planned implementation

1. Add logical CPU count and capacity-normalized utilization fields to
   discovery compute telemetry.
2. Add worker-capacity utilization so a 48-worker run can reveal whether work
   actually occupies the configured workers.
3. Add bottleneck hints for low worker utilization and artifact-write pressure.
4. Time parent-side runner artifact writes for resolved specs, state files,
   trial records, ledgers, and snapshots.
5. Add focused telemetry tests and run discovery/contract validation.
6. Record the resulting diagnostic boundaries in the stage report.

## Validation target

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_runner.py tests\research_discovery\test_compute_telemetry.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Exit evidence

- Upgraded discovery compute telemetry to
  `discovery-compute-telemetry-v2`.
- Added logical CPU count, worker-capacity CPU seconds, logical-capacity CPU
  seconds, process CPU percent of worker capacity, process CPU percent of
  logical capacity, active-worker-to-logical-CPU ratio, artifact-write wall
  share, and a nested `processor_utilization` diagnostic block.
- Added runner-side artifact write timing for resolved spec, run state, trial
  records, ledgers, and snapshots. The final manifest write is intentionally
  excluded from the persisted timing scope because telemetry is embedded before
  the final manifest is written.
- Added bottleneck hints for worker-capacity underutilization, logical CPU
  underutilization, and artifact-write pressure.
- Preserved the legacy raw `process_cpu_seconds`,
  `process_cpu_percent_single_core`, and `process_cpu_percent` fields.
- Existing R104 exact-sweep telemetry shows the concern clearly: `48` active
  workers, `112216.3899596` wall seconds, and `115309.46875` process CPU
  seconds, which is about one busy core rather than 48 busy workers. This
  packet makes that visible in future manifests; it does not claim a speedup.
- Validation passed:
  `python -m compileall -q src\tradingbotsuite`;
  `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_compute_telemetry.py tests\research_discovery\test_discovery_runner.py -q`
  (`17 passed`);
  `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
  (`180 passed`);
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  (`427 passed`);
  targeted performance-surface validation recommended by the subagent:
  `$env:PYTHONDONTWRITEBYTECODE='1'; $env:PYTHONPATH='src'; python -m pytest -q -p no:cacheprovider tests\research_discovery\test_compute_telemetry.py tests\research_discovery\test_discovery_runner.py::test_discovery_runner_writes_manifest_state_ledgers_and_snapshots tests\research_discovery\test_discovery_benchmark.py::test_discovery_benchmark_report_contains_research_only_gate_metrics tests\historical\test_full_cycle_synthetic.py::test_cycle_auto_backend_default_uses_fastest_exact_vector_route tests\historical\test_full_cycle_synthetic.py::test_full_cycle_expands_optimizer_search_spaces_and_writes_stability_regions tests\historical\test_research_cycle_benchmark.py::test_research_cycle_benchmark_report_contains_research_only_gate_metrics`
  (`6 passed`);
  `git diff --check` passed with CRLF normalization warnings only.
