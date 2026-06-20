# WPR106-233 Sandbox Artifact Analytics CLI

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Add a fast agent-facing analytics layer for Rapid Strategy Iteration Sandbox
runs. Agents should be able to summarize compact sandbox Parquet/JSON artifacts
without opening notebooks, scanning full tables manually, or treating sandbox
rows as candidate evidence.

## Scope

- Add sandbox artifact analytics that read an existing sandbox run directory
  and produce a compact JSON summary:
  - run boundary flags;
  - artifact paths;
  - status counts;
  - venue/family/exit/filter summaries;
  - rejection reason counts;
  - top-ranked rows;
  - evidence-request summary.
- Validate that analyzed manifests/results remain sandbox-only and
  non-promotable.
- Add a research CLI command `summarize-rapid-strategy-sandbox` that resolves
  `--run-dir` under the configured research output root, writes an
  `analysis_summary.json` file by default, and prints the summary payload.
- Register the command as research-owned and add boundary contract coverage.
- Add focused sandbox and live-boundary tests.
- Update sandbox docs and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-233-sandbox-artifact-analytics-cli.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_ANALYTICS_CLI_REPORT.md`
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

- Sandbox analytics can summarize a run written by the sandbox result store.
- The summary contains top rows, status counts, venue/family/exit/filter
  summaries, rejection reason counts, and evidence-request counts.
- The analysis payload and optional report file carry `research_only`,
  `observe_only`, `promotion_ready: false`, `sandbox_only`,
  `candidate_evidence: false`, and `candidate_pack_eligible: false`.
- The CLI rejects `--run-dir` outside the configured research output root.
- The CLI command is listed in the research command registry and boundary
  contract.
- Validation includes focused sandbox tests, CLI boundary tests, import-boundary
  tests, package compile, and the contract baseline.

## Boundary

This packet reads and summarizes sandbox artifacts only. It does not re-rank
strict evidence, write candidate packs, create paper/live signals, change
sizing, place orders, mutate runtime mode, write live configuration, or claim
promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. The packet added sandbox artifact
analytics, `analysis_summary.json` report writing, a
`summarize-rapid-strategy-sandbox` research CLI command, research-command
registry coverage, boundary-contract coverage, and focused tests for analytics
payloads, non-promotable ranking validation, CLI execution, and research-root
path rejection.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results were 33 sandbox tests passed, 9 CLI boundary tests passed, 11
import-boundary tests passed, package compileall passed, and 461 contract tests
passed.
