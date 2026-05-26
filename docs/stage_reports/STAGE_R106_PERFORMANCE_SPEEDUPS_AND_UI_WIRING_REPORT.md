# Stage R106 Performance Speedups And UI Wiring Report

Date: 2026-05-26
Work packet: `docs/work_packets/WPR106-20-performance-speedups-and-ui-wiring.md`

## Summary

WPR106-20 implements the safe speed and visibility improvements identified by
the WPR106-19 performance/utilization study. The work stayed research-only and
did not add live execution, live configuration writes, runtime-mode changes,
order placement, sizing behavior, candidate-pack writing, promotion readiness,
or performance/profit claims.

## Implementation

- Discovery compute telemetry now accepts observed artifact write counters from
  the runner and therefore avoids the broad recursive output-directory artifact
  scan when the current run has already observed the parent-process writes.
- Discovery manifests now expose finer finalization timing buckets:
  final batch snapshot/state write, final status state write, final ledger
  materialization, final snapshot/state write, and manifest assembly before
  telemetry serialization.
- Process-executor discovery runs now return per-chunk worker timing evidence:
  worker PID count, chunk count, total records, chunk wall time, chunk process
  CPU time, and worker context initialization timing. Telemetry also preserves
  the explicit note that parent process CPU excludes process-pool child CPU.
- Placeholder process-discovery runs no longer initialize the real-discovery
  context in each child process.
- Operator artifact/progress APIs now summarize discovery performance evidence:
  worker plan, cache hit rates, ETA/runtime fields, artifact write pressure,
  artifact count strategy/scope, stage timing, and process chunk timing.
- The operator artifact API now indexes the WPR106-19
  `measurement_summary.json` performance-utilization study as a first-class
  `performance_utilization_study` artifact.
- The Research UI now renders the discovery worker plan, cache hits, artifact
  pressure, process chunk timing, top runtime stages, active-progress
  performance details, and the performance-study one-line UI command without
  requiring the operator to inspect raw JSON.

## Validation

- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`

Result: all commands passed. The full operator UI pass emitted one existing
non-failing `aiosqlite` event-loop-close warning in
`test_operator_ui_disabled_returns_404`; no new blocking risk was found.

## Boundary

All new outputs and UI summaries remain `research_only`, `observe_only`, and
`promotion_ready: false`. The performance study is exposed as diagnostic
evidence only and does not authorize live usage or candidate promotion.
