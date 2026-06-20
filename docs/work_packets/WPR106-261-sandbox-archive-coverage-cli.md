# WPR106-261 Sandbox Archive Coverage CLI

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Expose the sandbox archive coverage matrix through a guarded research CLI
command so agents can generate venue/symbol/data-family/interval coverage
summaries from local archive manifests without writing Python glue.

## Scope

- Add `summarize-rapid-strategy-sandbox-archive-coverage` as a research-owned
  CLI command.
- Resolve inputs and outputs under the configured research output root using
  existing sandbox command allowlist patterns.
- Keep optional shared-market-data smoke mode consistent with archive audit.
- Register the command in the research command registry and live-boundary
  rejection tests.
- Add focused sandbox CLI tests for JSON/Parquet output and artifact catalog
  discovery.
- Update the sandbox contract and stage docs.

## Allowed Paths

- `docs/work_packets/WPR106-261-sandbox-archive-coverage-cli.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_COVERAGE_CLI_REPORT.md`
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

- The CLI command writes `archive_coverage_matrix.json` and
  `archive_coverage_matrix.parquet` under the configured research output root.
- The CLI command returns sandbox boundary flags, coverage counts, artifact
  paths, and descriptor/audit provenance in its JSON response.
- Optional shared-market-data smoke mode works when supplied and remains
  explicitly diagnostic.
- The command is registered as research-owned and rejected in live mode.
- Sandbox artifact catalog discovery includes the CLI-generated coverage
  matrix.
- Validation includes focused sandbox CLI tests, live CLI boundary tests,
  import-boundary tests, package compile, and the contract baseline when the
  local validation environment allows pytest-asyncio socket setup.

## Boundary

This packet adds a guarded read-only research CLI surface only. It does not
execute sandbox sweeps, execute strict validation, change strategy math, change
trial IDs, write candidate packs, create paper/live signals, define sizing,
place orders, change runtime mode, write live configuration, download provider
data, mutate source archive files, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. Added the
`summarize-rapid-strategy-sandbox-archive-coverage` research CLI command with
the same configured research output-root enforcement used by the other sandbox
commands. The command calls the existing archive coverage API, supports
optional shared-market-data smoke mode, writes sandbox JSON/Parquet coverage
artifacts, is registered as research-owned, and is rejected in live mode.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "archive_coverage or archive_coverage_under_research_root"
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q -k "archive_coverage or boundary_contract_lists_research_command_registry"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 2 focused sandbox archive-coverage tests passed, 2 focused live
boundary tests passed, 88 sandbox tests passed, 21 live CLI boundary tests
passed, package compileall passed, 11 import-boundary tests passed, and the
full contract baseline passed with 461 tests.
