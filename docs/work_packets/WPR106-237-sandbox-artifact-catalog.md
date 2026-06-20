# WPR106-237 Sandbox Artifact Catalog

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Add a bounded artifact catalog for Rapid Strategy Iteration Sandbox outputs so
agents can quickly find sandbox runs, suites, analysis reports, hypothesis
falsification indexes, and strict-validation request bundles under the research
output root without manually traversing directories.

## Scope

- Add a sandbox artifact catalog scanner for known sandbox JSON artifact names.
- Validate sandbox boundary flags on discovered artifact objects before
  indexing them.
- Write compact JSON and Parquet catalog artifacts:
  - `sandbox_artifact_catalog.json`;
  - `sandbox_artifact_catalog.parquet`.
- Include artifact kind, source artifact family, path, run/suite IDs, counts,
  strict-validation request bundle metadata, and modification timestamps.
- Add a research CLI command `index-rapid-strategy-sandbox-artifacts` with
  research-root `--root-dir` and optional `--output-dir` enforcement.
- Register the command as research-owned and add boundary contract coverage.
- Add focused sandbox and live-boundary tests.
- Update sandbox docs and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-237-sandbox-artifact-catalog.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_REPORT.md`
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

- A catalog scan finds sandbox run manifests, suite manifests, analysis
  reports, hypothesis falsification reports, and strict-validation request
  bundles under a research output root.
- The catalog validates sandbox boundary flags before indexing artifact
  objects.
- Catalog JSON and Parquet rows carry `research_only`, `observe_only`,
  `promotion_ready: false`, `sandbox_only`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- The CLI rejects `--root-dir` or `--output-dir` outside the configured
  research output root.
- The CLI command is listed in the research command registry and boundary
  contract.
- Validation includes focused sandbox tests, CLI boundary tests,
  import-boundary tests, package compile, and the contract baseline.

## Boundary

This packet indexes existing sandbox artifacts only. It does not execute
sandbox runs, execute strict validation, write candidate packs, create
paper/live signals, define sizing, place orders, mutate runtime mode, write
live configuration, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. The packet added bounded sandbox artifact
catalog scanning, known-artifact boundary validation, JSON/Parquet catalog
writing, `index-rapid-strategy-sandbox-artifacts` CLI wiring,
research-command registry coverage, boundary-contract coverage, and focused
tests for cataloging generated run/suite/report/bundle artifacts, CLI
execution, and research-root path rejection.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results were 45 sandbox tests passed, 13 CLI boundary tests passed, 11
import-boundary tests passed, package compileall passed, and 461 contract tests
passed.
