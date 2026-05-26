# WPR106-11 Windows Run-State Atomic Replace Retry

Status: complete

## Scope

Investigate and fix the latest failed BTC exact-discovery operator job
`run-discovery-5b8013f779ef43c28a8c3567a14d14a4`, which advanced durable trial
files but failed while replacing `run_state.json` on Windows with
`WinError 5: access denied`.

## Allowed paths

- `src/tradingbotsuite/research_discovery/snapshots.py`
- `tests/research_discovery/test_discovery_snapshots.py`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/work_packets/WPR106-11-windows-run-state-atomic-replace-retry.md`

## Constraints

- Do not delete or rewrite durable trial records.
- Do not lower the performance-first discovery worker cap.
- Keep retry behavior idle unless Windows/file-system contention occurs.
- Preserve research-only, observe-only, and `promotion_ready: false` semantics.

## Acceptance

- Atomic JSON writes retry transient Windows replace failures.
- The active BTC run state is reconciled to the durable trial-file count.
- Focused snapshot and discovery-runner tests pass.

## Closure

The failed job was a Windows atomic-replace contention, not lost discovery
work. Operator job `run-discovery-5b8013f779ef43c28a8c3567a14d14a4` advanced
durable BTC exact-discovery trial files to 531077, but `Path.replace()` failed
when moving a temp checkpoint over `run_state.json`.

`atomic_write_json()` now retries transient `PermissionError` replace failures
using env-tunable settings:

- `TBS_ATOMIC_WRITE_REPLACE_ATTEMPTS` (default 60)
- `TBS_ATOMIC_WRITE_REPLACE_BACKOFF_SECONDS` (default 0.05)

The normal successful write path has no sleep. The retry only activates after
Windows/file-system contention.

A zero-trial resume reconciled the active run:

- Completed trial IDs: 531077
- Completed hashes: 531077
- Durable trial files: 531077
- Remaining trials: 39163
- Recovered lagging files: 344

Validation:

- `python -m compileall -q src\tradingbotsuite\research_discovery`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_snapshots.py tests\research_discovery\test_discovery_runner.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
