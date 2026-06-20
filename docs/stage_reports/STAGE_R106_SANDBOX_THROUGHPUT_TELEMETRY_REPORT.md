# Stage R106 Sandbox Throughput Telemetry Report

Date: 2026-06-20
Packet: `WPR106-372-sandbox-throughput-telemetry-report`

## Summary

WPR106-372 adds measurement-only throughput telemetry to one-command rapid
strategy sandbox iteration manifests and adds
`summarize-rapid-strategy-sandbox-throughput` for existing iteration manifests.

Recorded iteration telemetry includes total runtime, per-stage runtime,
process-local market-data frame cache hit/miss counts, source-integrity cache
hit/miss counts, 2024+ rows loaded, source bytes read, workers requested/used,
and traced peak memory when measurable. The report command writes
`sandbox_throughput_report.json`,
`sandbox_throughput_iteration_summary.parquet`, and
`sandbox_throughput_stage_summary.parquet` with cache summaries, artifact-byte
estimates, missing-telemetry blockers, and bottleneck ranking.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "throughput_telemetry"`
  - `3 passed, 188 deselected`
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  - `26 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `205 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `461 passed`
- `git diff --check`
  - passed with existing LF-to-CRLF warnings only

## Boundary Statement

Telemetry and reports are diagnostic only. They do not change trial identity,
ranking, strategy signals, exit/fill semantics, archive routing, blocker
semantics, evidence-request selection, strict validation, candidate packs,
paper/live behavior, sizing, order placement, runtime mode, live configuration,
candidate-evidence semantics, or promotion state. Reports explicitly keep
`speedup_claimed: false`.
