# WPR106-08 Exact Discovery Process Worker Guard And Runtime Probe

Status: complete

## Scope

Investigate and fix the failed R106 BTC exact discovery run:

- Diagnose the latest `run-discovery` failure that terminated the process pool
  before trial records were persisted.
- Add a real-data process-worker guard so expanded candidate-depth fixtures do
  not fan out into unsafe per-process context duplication by default.
- Replace the candidate-depth KNN row-by-row exact neighbor scan with an exact
  batched nearest-neighbor path where split boundaries make that safe.
- Record the configured, requested, and capped worker plan in discovery
  manifests and compute telemetry.
- Persist completed process chunks before waiting for later submitted chunks so
  a late child-process failure does not discard already-returned trial records.
- Execute real-discovery pending trials in cache-affinity order while preserving
  trial ID to payload mapping, so exhaustive candidate-depth sweeps reuse label
  and neighbor caches instead of randomizing the most expensive dimensions.
- Run focused discovery tests plus a bounded real-data runtime probe to verify
  resume safety, process stability, throughput, and ETA behavior.

## Allowed paths

- `src/tradingbotsuite/research_discovery/runner.py`
- `src/tradingbotsuite/research_discovery/knn_study.py`
- `src/tradingbotsuite/research_discovery/event_accounting.py`
- `tests/research_discovery/test_discovery_runner.py`
- `tests/research_discovery/test_knn_study.py`
- `tests/research_discovery/test_event_accounting.py`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/work_packets/WPR106-08-exact-discovery-process-worker-guard-and-runtime-probe.md`
- `docs/stage_reports/STAGE_R106_EXACT_DISCOVERY_PROCESS_WORKER_GUARD_AND_RUNTIME_PROBE_REPORT.md`

## Constraints

- Do not modify generated historical data catalog evidence or completed cycle
  artifacts.
- Preserve research-only, observe-only, and `promotion_ready: false` discovery
  outputs.
- Do not weaken exact discovery gates or reinterpret old/simple discovery
  results as completed R106 evidence.
- Keep the active exact specs stable; runtime capping should be observable
  without changing the configured 48-worker request.

## Acceptance

- A failed stable discovery run with zero trial records can be resumed without
  deleting its output directory.
- Real-data process discovery caps active child processes by default and allows
  explicit override through an environment variable.
- Manifest and compute telemetry expose configured workers, requested workers,
  active workers, cap source, and cap reason.
- Process chunks are checkpointed as they return rather than only after the
  entire submission batch succeeds.
- Focused discovery tests pass.
- A bounded real-data probe completes without abrupt process-pool termination
  and reports measured throughput/ETA.

## Closure evidence

- Latest failed BTC exact-discovery run was recovered in place; persisted trial
  records and `run_state.json` advanced from 128 completed trials to 512
  completed trials through bounded resume probes without deleting output.
- Process execution now caps expanded real-discovery runs at eight active child
  workers by default while preserving the configured 48-worker request in
  manifest telemetry; `TBS_DISCOVERY_REAL_PROCESS_MAX_WORKERS` remains the
  explicit override.
- Real-discovery process chunks are persisted as futures complete, process-pool
  crashes raise a contextual error, and completed trial JSON files remain the
  resume source of truth.
- Screening KNN now computes one relaxed exact base per cache group, reuses
  threshold metric arrays, caches no-regime baselines, defers heavy inline
  artifacts for `interesting_only` sweeps, and uses full cache-group chunks for
  no-stop production discovery runs.
- Final bounded BTC probe completed 64 additional candidate-depth trials in
  610.7 seconds. Base KNN misses averaged 365.2 seconds; base-hit non-artifact
  threshold trials averaged 0.379 seconds; no heavy artifacts were written.
  With 108 cache groups, 8 active workers, and full cache-group chunks, the
  measured full-run estimate is roughly 9 to 12 wall-clock hours on this
  machine, below the 30-hour target.
