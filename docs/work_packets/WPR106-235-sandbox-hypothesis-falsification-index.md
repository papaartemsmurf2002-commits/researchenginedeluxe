# WPR106-235 Sandbox Hypothesis Falsification Index

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Add hypothesis-level falsification summaries for Rapid Strategy Iteration
Sandbox artifacts. Agents should be able to quickly see which hypotheses were
blocked by missing inputs, falsified by sandbox evidence, inconclusive, or worth
strict validation requests without scanning row-level rankings manually.

## Scope

- Add sandbox hypothesis falsification analytics for a single sandbox run.
- Add sandbox hypothesis falsification analytics for a sandbox suite by reading
  its suite manifest/index and per-run artifacts.
- Write compact JSON and Parquet hypothesis indexes:
  - `hypothesis_falsification.json`;
  - `hypothesis_falsification.parquet`;
  - `suite_hypothesis_falsification.json`;
  - `suite_hypothesis_falsification.parquet`.
- Preserve sandbox-only boundary flags on reports and rows.
- Add a research CLI command
  `summarize-rapid-strategy-sandbox-hypotheses` with mutually exclusive
  `--run-dir` and `--suite-dir` inputs under the configured research output
  root.
- Register the command as research-owned and add boundary contract coverage.
- Add focused sandbox and live-boundary tests.
- Update sandbox docs and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-235-sandbox-hypothesis-falsification-index.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_HYPOTHESIS_FALSIFICATION_INDEX_REPORT.md`
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

- A run-level hypothesis report groups rankings by hypothesis and includes
  tested venues, symbols, exits, filters, best trial metrics, evidence-request
  trial IDs, blocker/rejection summaries, and a falsification decision.
- A suite-level hypothesis report combines all suite case run artifacts and
  records suite/case/run provenance.
- Decisions distinguish at least strict-validation requests, sandbox-falsified
  hypotheses, missing-input blockers, and inconclusive/mixed outcomes.
- Report JSON and Parquet rows carry `research_only`, `observe_only`,
  `promotion_ready: false`, `sandbox_only`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- The CLI rejects `--run-dir` or `--suite-dir` outside the configured research
  output root.
- The CLI command is listed in the research command registry and boundary
  contract.
- Validation includes focused sandbox tests, CLI boundary tests,
  import-boundary tests, package compile, and the contract baseline.

## Boundary

This packet summarizes sandbox artifacts only. It does not execute strict
validation, write candidate packs, create paper/live signals, define sizing,
place orders, mutate runtime mode, write live configuration, or claim promotion
readiness.

## Completion Notes

Implemented and closed on 2026-06-18. The packet added run-level and
suite-level hypothesis falsification analytics, JSON/Parquet report writing,
`summarize-rapid-strategy-sandbox-hypotheses` CLI wiring, research-command
registry coverage, boundary-contract coverage, and focused tests for requested
strict-validation labels, sandbox-falsified labels, suite aggregation, CLI
execution, and research-root path rejection.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results were 40 sandbox tests passed, 11 CLI boundary tests passed, 11
import-boundary tests passed, package compileall passed, and 461 contract tests
passed.
