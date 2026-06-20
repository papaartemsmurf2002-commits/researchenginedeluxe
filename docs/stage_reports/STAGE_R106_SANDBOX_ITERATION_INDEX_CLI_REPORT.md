# Stage R106 Sandbox Iteration Index CLI Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-265-sandbox-iteration-index-cli.md`
Status: closed

## Summary

WPR106-265 exposes sandbox iteration indexes through a guarded research CLI
command:
`index-rapid-strategy-sandbox-iterations`.

## Implementation

- Added the CLI parser, handler, and dispatch path in
  `src/tradingbotsuite/main.py`.
- Registered the command in `tradingbotsuite.research.command_registry`.
- Documented the command in `docs/contracts/boundary_contract.md` and the
  sandbox research contract.
- The command resolves optional `--root-dir` and `--output-dir` under the
  configured research output root.
- The command calls `build_sandbox_iteration_index()` and returns its sandbox
  JSON payload.
- Added focused sandbox CLI coverage and live-boundary path rejection tests.

## Boundary

The packet adds a guarded read-only research CLI over existing sandbox
iteration artifacts. It does not execute sandbox sweeps, execute strict
validation, write candidate artifacts, change strategy math, change trial IDs,
create paper/live signals, define sizing, place orders, mutate runtime mode,
write live configuration, download provider data, mutate source archive files,
or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index or indexes_sandbox_iterations"
# 3 passed, 92 deselected

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q -k "sandbox_iterations or boundary_contract_lists_research_command_registry"
# 2 passed, 20 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 95 passed

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
# 22 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

The iteration index is available through both Python API and guarded CLI. Later
packets can expose index summaries in the operator UI if useful.
