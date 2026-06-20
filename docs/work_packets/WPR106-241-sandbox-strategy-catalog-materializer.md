# WPR106-241 Sandbox Strategy Catalog Materializer

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Add a normalized strategy catalog materializer for the Rapid Strategy Iteration
Sandbox. Agents should be able to compile existing strategy spreadsheets,
lead catalogs, repo strategy configs, or directories into a reusable sandbox
strategy catalog artifact before running archive-backed sweeps.

## Scope

- Add a sandbox strategy catalog materializer for local CSV, TSV, JSON, Parquet,
  XLSX, and XLS strategy/catalog/config files.
- Reuse the existing sandbox `load_strategy_catalog` compiler so precomputed
  signal rows, repo strategy configs, and spreadsheet-like lead rows all follow
  the established strategy intake rules.
- Support one or more catalog roots and recursive directory discovery for
  agent workflow speed.
- Write compact research-only artifacts:
  - `strategy_catalog.json`;
  - `strategy_catalog.parquet`;
  - `strategy_catalog_build_report.json`;
  - `strategy_catalog_build_report.parquet`.
- Report source paths, included/skipped status, row counts, hypothesis/family
  counts, blueprint IDs, signal columns, and skip reasons.
- Keep repeated builds deterministic and idempotent for agent preflight loops.
- Add a research CLI command `build-rapid-strategy-sandbox-strategy-catalog`
  with research-root `--output-dir` enforcement.
- Register the command as research-owned and add boundary contract coverage.
- Add focused sandbox and live-boundary tests.
- Update sandbox docs and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-241-sandbox-strategy-catalog-materializer.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_STRATEGY_CATALOG_MATERIALIZER_REPORT.md`
- `docs/contracts/boundary_contract.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/command_registry.py`
- `src/tradingbotsuite/research_sandbox/**`
- `tests/research_sandbox/**`
- `tests/live/test_cli_boundary.py`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- The materializer writes a loadable `strategy_catalog.json` artifact from
  local strategy files and directories.
- Generated catalog rows carry the sandbox boundary flags inherited from
  `StrategyCatalogRow.to_payload()`.
- Unsupported files or files that cannot compile are skipped with explicit
  reasons.
- The build report carries `research_only`, `observe_only`,
  `promotion_ready: false`, `sandbox_only`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- Repeated builds with the same roots refresh the same deterministic artifact
  directory.
- The CLI rejects `--output-dir` outside the configured research output root.
- The CLI command is listed in the research command registry and boundary
  contract.
- Validation includes focused sandbox tests, CLI boundary tests,
  import-boundary tests, package compile, and the contract baseline when the
  local validation environment allows pytest-asyncio socket setup.

## Boundary

This packet materializes sandbox strategy catalog descriptors only. It does not
execute strategy sweeps, execute strict validation, write candidate packs,
create paper/live signals, define sizing, place orders, mutate runtime mode,
write live configuration, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. The packet added a normalized sandbox
strategy catalog materializer, recursive multi-root source discovery, reused
the existing strategy catalog loader/compiler, deterministic output directory
IDs, loadable `strategy_catalog.json` artifacts, compact strategy/report
Parquet artifacts, skipped-source reason reporting, artifact-catalog discovery
for generated catalogs/reports, CLI wiring for
`build-rapid-strategy-sandbox-strategy-catalog`, research-command registry
coverage, boundary-contract coverage, sandbox contract coverage, and focused
tests for mixed-source materialization, idempotent preflight refresh, CLI
execution, catalog indexing, and research-root path rejection.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final focused results were 58 sandbox tests passed, 17 CLI boundary tests
passed, 11 import-boundary tests passed, and package compileall passed. The
full contract baseline was attempted and reached 460 passed tests before
failing during pytest-asyncio event-loop socketpair setup for one async
contract test with Windows `WinError 10055`, before the test body ran.
`ISSUE-R106-026` tracks this local validation-environment blocker.
