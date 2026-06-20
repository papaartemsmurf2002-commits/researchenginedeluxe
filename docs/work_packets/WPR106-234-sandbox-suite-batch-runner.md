# WPR106-234 Sandbox Suite Batch Runner

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Add a bounded batch runner for the Rapid Strategy Iteration Sandbox so agents
can execute several sandbox specs/catalogs/venue manifests in one command and
get a compact suite-level index. The runner should improve rapid hypothesis
iteration without creating candidate evidence or broadening into live/paper
workflow.

## Scope

- Add a sandbox suite spec loader for JSON files with a `suite_id` and a list
  of cases. Each case references a sandbox run spec, strategy catalog, venue
  archive manifest, optional shared market data path, optional request score
  threshold, and optional label/description.
- Resolve suite-relative case paths deterministically.
- Execute each case with the existing archive-routed sandbox runner.
- Summarize each run with the existing sandbox analysis layer.
- Write suite-level artifacts under the configured research output root:
  - `suite_manifest.json`;
  - `suite_index.json`;
  - `suite_index.parquet`;
  - `suite_evidence_requests.json`;
  - `suite_evidence_requests.parquet`.
- Preserve sandbox-only boundary flags on suite specs, manifests, indexes, and
  aggregated evidence-request descriptors.
- Add a research CLI command `run-rapid-strategy-sandbox-suite`.
- Register the command as research-owned and add boundary contract coverage.
- Add focused sandbox and live-boundary tests.
- Update sandbox docs and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-234-sandbox-suite-batch-runner.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_SUITE_BATCH_RUNNER_REPORT.md`
- `docs/contracts/boundary_contract.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `configs/sandbox/**`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/command_registry.py`
- `src/tradingbotsuite/research_sandbox/**`
- `tests/research_sandbox/**`
- `tests/live/test_cli_boundary.py`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- A suite spec can run at least two sandbox cases and write per-run artifacts
  plus a suite manifest/index.
- Suite indexes include case IDs, run IDs, run directories, result counts,
  screened/rejected/blocked counts, top trial IDs, evidence-request counts, and
  market-source summaries.
- Aggregated evidence-request artifacts contain only sandbox evidence-request
  descriptors with `research_only`, `observe_only`, `promotion_ready: false`,
  `sandbox_only`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- Suite case paths resolve relative to the suite spec file.
- The CLI resolves `--output-dir` under the configured research output root and
  is rejected by the live-mode research-command guard.
- The CLI command is listed in the research command registry and boundary
  contract.
- Validation includes focused sandbox tests, CLI boundary tests,
  import-boundary tests, package compile, and the contract baseline.

## Boundary

This packet orchestrates existing sandbox runs and writes sandbox-only suite
indexes. It does not execute strict validation, write candidate packs, create
paper/live signals, change sizing, place orders, mutate runtime mode, write
live configuration, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. The packet added suite spec/case
loading, suite-relative case path resolution, multi-case sandbox execution,
suite-level JSON/Parquet indexes, aggregated evidence-request descriptor
artifacts, `run-rapid-strategy-sandbox-suite` CLI wiring, research-command
registry coverage, boundary-contract coverage, and focused tests for suite
execution, path resolution, unsafe ID rejection, live-boundary flag rejection,
CLI execution, and research-root path rejection.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results were 37 sandbox tests passed, 10 CLI boundary tests passed, 11
import-boundary tests passed, package compileall passed, and 461 contract tests
passed. The first full contract attempt reached 460 passed tests and failed
only during Windows asyncio event-loop setup with `WinError 10055`; the full
contract baseline reran cleanly with 461 passed.
