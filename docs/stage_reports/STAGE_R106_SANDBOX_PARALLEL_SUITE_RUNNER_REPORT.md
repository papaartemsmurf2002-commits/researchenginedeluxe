# Stage R106 Sandbox Parallel Suite Runner Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-251-sandbox-parallel-suite-runner.md`
Status: closed

## Summary

WPR106-251 improves agent workflow speed for archive-backed sandbox batches by
allowing independent suite cases to run concurrently. Serial execution remains
the default, and parallel output is normalized back into suite spec order before
artifacts are written.

## Implementation

- Added `max_workers` to `run_sandbox_suite()` in
  `src/tradingbotsuite/research_sandbox/suite.py`.
- Refactored case execution into an isolated helper that performs the existing
  load, preflight, archive sweep, analysis, and evidence-request collection
  for one case.
- Uses `ThreadPoolExecutor` only when `max_workers > 1` and more than one case
  exists.
- Preserves deterministic suite output by sorting completed case executions by
  the original suite case index before writing JSON/Parquet indexes and
  aggregated evidence requests.
- Records `max_workers` in the suite manifest as orchestration metadata.
- Added `--max-workers` to `run-rapid-strategy-sandbox-suite` and returns the
  selected value in the CLI payload.
- The change does not alter strategy math, sweep scoring, deterministic trial
  IDs, preflight gates, descriptor archive routing, or sandbox boundary fields.

## Boundary

This packet changes sandbox suite orchestration throughput only. It does not
execute strict validation, write candidate packs, create live/paper signals,
define sizing, place orders, change runtime mode, write live configuration,
download provider data, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 76 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# final rerun: 461 passed

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
# 19 passed
```

The first full-contract attempt reached 460 passed tests and failed during
pytest-asyncio event-loop socket setup with Windows `WinError 10055`, matching
the already tracked local validation-environment issue. A rerun passed with
461 tests.

## Remaining Work

Parallel suites now speed independent case batches. Later optimization should
profile full archive-backed agent iterations to decide whether catalog
materialization, archive manifest building, preflight, or artifact analysis is
the next practical bottleneck.
