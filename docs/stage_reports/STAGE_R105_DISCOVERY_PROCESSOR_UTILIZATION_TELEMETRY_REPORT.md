# Stage R105 Discovery Processor Utilization Telemetry Report

Date: 2026-05-19
Owner: Codex Research Agent
Stage: R105 candidate factory component falsification
Status: telemetry and artifact-write timing complete; execution semantics unchanged

## Research Boundary

This packet is telemetry-only. It does not change discovery scoring, KNN
behavior, search-space generation, candidate-pack gates, live execution,
runtime mode, order placement, live configuration, promotion behavior, or
sizing behavior. All telemetry remains research-only, observe-only, and
`promotion_ready: false`.

## Implemented

`src/tradingbotsuite/research_discovery/telemetry.py` now emits
`discovery-compute-telemetry-v2` with:

- `logical_cpu_count`
- `worker_capacity_cpu_seconds`
- `logical_capacity_cpu_seconds`
- `process_cpu_percent_of_worker_capacity`
- `process_cpu_percent_of_logical_capacity`
- `active_worker_to_logical_cpu_ratio`
- `artifact_write_wall_time_share`
- nested `processor_utilization` payload
- processor diagnostic reasons:
  - `worker_capacity_underutilized`
  - `logical_cpu_capacity_underutilized`
  - `artifact_write_pressure`
  - `no_processor_utilization_bottleneck_flagged`

Legacy raw fields remain available:

- `process_cpu_seconds`
- `process_cpu_percent_single_core`
- `process_cpu_percent`

`src/tradingbotsuite/research_discovery/runner.py` now records parent-side
artifact write duration for resolved spec, run state, trial records, ledgers,
and snapshots. The persisted telemetry scope is
`runner_parent_resolved_spec_state_trial_records_ledgers_snapshots_excludes_final_manifest_write`;
the final manifest write is excluded because telemetry is embedded before that
write occurs.

## Existing R104 Evidence

The completed R104 BTCUSDT exact sweep already shows the processor-utilization
problem:

| Field | Value |
| --- | ---: |
| Active workers | `48` |
| Wall seconds | `112216.3899596` |
| Process CPU seconds | `115309.46875` |
| Single-core CPU percent | `102.75635207255694` |
| Trials per minute | `304.8966377577983` |
| Artifact files | `570374` |
| Artifact bytes | `2195792196` |

That means the run consumed roughly one busy core over a 31.2-hour wall-clock
run despite nominally using 48 worker threads. The old telemetry did not make
that worker-capacity gap explicit. It also did not provide useful parent-side
artifact write timing for this sweep; future manifests will expose both the
worker-capacity gap and observed artifact-write wall-share.

## Interpretation

This packet does not claim a performance fix. It makes the bottleneck visible
and machine-readable, including whether time is disappearing into parent-side
artifact writes. The next performance packet should target the scheduler or
work unit design directly. Based on R104 evidence and R105 postmortem
signatures, the likely useful path is to avoid scheduling redundant parameter
trials and to batch threshold/score variants around reusable prediction
ledgers before considering Windows process-pool execution.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_compute_telemetry.py tests\research_discovery\test_discovery_runner.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONDONTWRITEBYTECODE='1'; $env:PYTHONPATH='src'; python -m pytest -q -p no:cacheprovider tests\research_discovery\test_compute_telemetry.py tests\research_discovery\test_discovery_runner.py::test_discovery_runner_writes_manifest_state_ledgers_and_snapshots tests\research_discovery\test_discovery_benchmark.py::test_discovery_benchmark_report_contains_research_only_gate_metrics tests\historical\test_full_cycle_synthetic.py::test_cycle_auto_backend_default_uses_fastest_exact_vector_route tests\historical\test_full_cycle_synthetic.py::test_full_cycle_expands_optimizer_search_spaces_and_writes_stability_regions tests\historical\test_research_cycle_benchmark.py::test_research_cycle_benchmark_report_contains_research_only_gate_metrics
git diff --check
```

Results:

- focused telemetry/runner tests: `17 passed`
- `tests/research_discovery`: `180 passed`
- `tests/contracts`: `427 passed`
- targeted performance-surface validation: `6 passed`
- `git diff --check`: passed with CRLF normalization warnings only

## Next Work

Open a scheduler/effective-work packet that reduces redundant exact-sweep work
before running another coupled brute-force search. The R105 postmortem shows
570240 scheduled/effective parameter keys but only 564 ledger-level prediction
signatures and 38 entry signatures in the available artifacts, so batching or
deduping work units is likely more valuable than simply raising thread counts.
