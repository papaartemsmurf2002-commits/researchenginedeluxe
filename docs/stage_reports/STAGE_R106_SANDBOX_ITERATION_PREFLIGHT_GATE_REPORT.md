# Stage R106 Sandbox Iteration Preflight Gate Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-245-sandbox-iteration-preflight-gate.md`
Status: closed

## Summary

WPR106-245 makes compatibility preflight part of the default one-command
sandbox agent iteration. Agents no longer need to remember a separate preflight
command to see whether a strategy/archive matrix has runnable trials before the
sweep begins.

## Implementation

- Added a versioned preflight gate to `run_sandbox_agent_iteration()`.
- Runs `preflight_sandbox_compatibility()` after input materialization/loading
  and before `run_sandbox_archive_sweep()`.
- Writes preflight artifacts under the iteration directory.
- Adds a `compatibility_preflight` row to `sandbox_iteration_steps.parquet`.
- Adds preflight JSON/Parquet paths, row counts, status counts,
  runnable/blocked trial estimates, and blocker reason counts to
  `sandbox_iteration_manifest.json`.
- Preserves the existing runnable iteration path: archive sweep, analysis,
  hypothesis falsification, descriptor-only validation request bundle export,
  and global leaderboard refresh still run when preflight finds runnable
  trials.
- Adds a zero-runnable short path: the iteration writes a final
  `blocked_by_preflight` manifest and marks archive sweep, analysis,
  falsification, validation bundle, and leaderboard steps as skipped.

## Boundary

This packet changes orchestration only. It does not alter sandbox scoring math,
execute strict validation, write candidate packs, create paper/live signals,
define sizing, place orders, mutate runtime mode, write live configuration,
download provider data, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 68 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# final rerun: 461 passed
```

The first full-contract attempt reached 460 passed tests and failed during
pytest-asyncio event-loop socket setup with Windows `WinError 10055`, matching
the already tracked local validation-environment issue. A rerun passed with
461 tests.

## Remaining Work

The preflight gate does not tune strategy parameters or select venues. It only
keeps agent iterations from spending time on a sweep when the resolved
strategy/catalog/archive matrix has no runnable trials.
