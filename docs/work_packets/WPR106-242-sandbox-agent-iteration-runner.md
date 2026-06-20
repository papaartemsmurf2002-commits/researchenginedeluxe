# WPR106-242 Sandbox Agent Iteration Runner

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Add a one-command Rapid Strategy Iteration Sandbox workflow for agents. The
workflow should materialize or reuse strategy catalogs and venue archive
manifests, run archive-backed sandbox sweeps, summarize/falsify results, export
descriptor-only strict-validation request bundles, refresh the global
leaderboard, and write a compact iteration manifest.

## Scope

- Add a research-only sandbox iteration orchestrator around existing sandbox
  components.
- Accept either existing `strategy_catalog.json` / `venue_archives.json` inputs
  or local catalog/archive roots that are materialized before the run.
- Load an existing sandbox run spec or use a small default 2024+ spec for agent
  preflight runs.
- Run the existing archive-backed sweep path only; do not add a new backtest
  engine.
- Write an iteration manifest JSON plus optional Parquet step index with paths
  to materialized catalogs, archive manifests, run artifacts, summary,
  hypothesis falsification, validation request bundle, and global leaderboard.
- Preserve deterministic run IDs/trial IDs through the existing sandbox runner
  and record a deterministic iteration ID.
- Add a research CLI command `run-rapid-strategy-sandbox-iteration` with
  research-root enforcement for output and optional existing artifact paths.
- Register the command as research-owned and add boundary contract coverage.
- Add focused sandbox and live-boundary tests.
- Update sandbox docs and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-242-sandbox-agent-iteration-runner.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_AGENT_ITERATION_RUNNER_REPORT.md`
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

- The iteration runner can start from catalog roots and archive roots, write
  materialized inputs, run an archive-backed sweep, summarize/falsify it,
  export descriptor-only validation requests, refresh a global leaderboard, and
  write an iteration manifest.
- The iteration runner can start from existing materialized strategy catalog
  and venue archive manifest files without rebuilding those inputs.
- All generated iteration artifacts carry `research_only`, `observe_only`,
  `promotion_ready: false`, `sandbox_only`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- The validation bundle remains descriptor-only and records strict validation
  as not executed.
- The CLI rejects `--output-dir` outside the configured research output root
  while allowing local source/input roots to remain normal read-only inputs.
- The CLI command is listed in the research command registry and boundary
  contract.
- Validation includes focused sandbox tests, CLI boundary tests,
  import-boundary tests, package compile, and the contract baseline when the
  local validation environment allows pytest-asyncio socket setup.

## Boundary

This packet orchestrates existing sandbox research-only workflows. It does not
execute strict validation, write candidate packs, create paper/live signals,
define sizing, place orders, mutate runtime mode, write live configuration, add
provider downloads, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. The packet added a one-command sandbox
agent iteration runner, `run_sandbox_agent_iteration`, plus CLI command
`run-rapid-strategy-sandbox-iteration`. The workflow can materialize local
strategy roots and archive roots or reuse existing materialized
`strategy_catalog.json` and `venue_archives.json` files, run the existing
archive-backed sandbox sweep, write run summary and hypothesis falsification
artifacts, export descriptor-only strict-validation request bundles, refresh a
global leaderboard, and write a sandbox iteration manifest plus Parquet step
index. Repeated calls with the same content-based iteration identity return the
existing manifest instead of colliding with the existing run directory.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results were 61 sandbox tests passed, 18 CLI boundary tests passed, 11
import-boundary tests passed, package compileall passed, and 461 contract tests
passed.
