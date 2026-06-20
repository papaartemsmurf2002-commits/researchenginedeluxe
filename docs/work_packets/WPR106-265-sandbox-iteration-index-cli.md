# WPR106-265 Sandbox Iteration Index CLI

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Expose the sandbox iteration index through a guarded research CLI command so
agents can generate cross-iteration navigation artifacts under the configured
research output root without writing Python glue.

## Scope

- Add `index-rapid-strategy-sandbox-iterations` as a research-owned CLI
  command.
- Resolve optional `--root-dir` and `--output-dir` under the configured
  research output root using existing sandbox CLI allowlist patterns.
- Call `build_sandbox_iteration_index()` and return its JSON payload.
- Register the command in the research command registry and live-boundary
  documentation/tests.
- Add focused sandbox CLI tests for JSON/Parquet output and artifact catalog
  discovery.
- Update the sandbox research contract, boundary contract, active index, stage
  ledger, and stage report.

## Allowed Paths

- `docs/work_packets/WPR106-265-sandbox-iteration-index-cli.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_INDEX_CLI_REPORT.md`
- `docs/contracts/boundary_contract.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/command_registry.py`
- `tests/research_sandbox/**`
- `tests/live/test_cli_boundary.py`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- The CLI command writes `sandbox_iteration_index.json` and
  `sandbox_iteration_index.parquet` under the configured research output root.
- The CLI command validates root/output allowlists and rejects output paths
  outside the research output root.
- The command is registered as research-owned and rejected in live mode.
- Sandbox artifact catalog discovery includes CLI-generated `iteration_index`
  artifacts.
- Validation includes focused sandbox CLI tests, focused live-boundary tests,
  full sandbox tests, package compile, import-boundary tests, and the contract
  baseline when the local environment allows it.

## Boundary

This packet only adds a guarded read-only research CLI over existing sandbox
iteration artifacts. It does not execute sandbox sweeps, execute strict
validation, write candidate artifacts, change strategy math, change trial IDs,
create paper/live signals, define sizing, place orders, mutate runtime mode,
write live configuration, download provider data, mutate source archive files,
or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. Added the
`index-rapid-strategy-sandbox-iterations` research CLI command, registered it
for live-mode rejection, and documented its sandbox boundary. The command
resolves optional `--root-dir` and `--output-dir` under the configured research
output root, calls `build_sandbox_iteration_index()`, and writes only sandbox
iteration index JSON/Parquet artifacts.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index or indexes_sandbox_iterations"
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q -k "sandbox_iterations or boundary_contract_lists_research_command_registry"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 3 focused sandbox iteration-index tests passed, 2 focused
live-boundary tests passed, 95 sandbox tests passed, 22 live CLI boundary tests
passed, package compileall passed, 11 import-boundary tests passed, and 461
contract tests passed.
