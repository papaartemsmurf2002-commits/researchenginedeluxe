# Stage R106 Sandbox Archive Coverage CLI Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-261-sandbox-archive-coverage-cli.md`
Status: closed

## Summary

WPR106-261 exposes the sandbox archive coverage matrix through a guarded
research CLI command:
`summarize-rapid-strategy-sandbox-archive-coverage`.

## Implementation

- Added the CLI parser, handler, and dispatch path in
  `src/tradingbotsuite/main.py`.
- Registered the command in `tradingbotsuite.research.command_registry`.
- Documented the command in `docs/contracts/boundary_contract.md` and the
  sandbox research contract.
- The command resolves optional `--output-dir` under the configured research
  output root and writes coverage JSON/Parquet artifacts.
- Optional `--market-data` preserves the existing shared-market-data smoke
  mode from archive audit and coverage APIs.
- Added focused sandbox CLI coverage tests and live-boundary output-root tests.

## Boundary

The packet adds a guarded read-only research CLI surface only. It does not
execute sandbox sweeps, execute strict validation, change strategy math, change
trial IDs, write candidate packs, create paper/live signals, define sizing,
place orders, change runtime mode, write live configuration, download provider
data, mutate source archive files, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "archive_coverage or archive_coverage_under_research_root"
# 2 passed, 86 deselected

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q -k "archive_coverage or boundary_contract_lists_research_command_registry"
# 2 passed, 19 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 88 passed

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
# 21 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

The coverage matrix is now available through both Python API and guarded CLI.
Later packets can add UI exposure if operator-side archive coverage navigation
becomes necessary, but this packet intentionally stays CLI/API only.
