# WPR106-240 Sandbox Global Leaderboard

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Add a global leaderboard for accumulated Rapid Strategy Iteration Sandbox runs.
Agents should be able to scan a research output root and quickly see which
hypotheses were blocked, falsified, screened positive, or emitted
strict-validation request descriptors across multiple archive-backed
iterations.

## Scope

- Add a sandbox global leaderboard scanner over existing sandbox `manifest.json`
  run artifacts under a research output root.
- Read and validate run manifests, rankings Parquet files, and evidence-request
  JSON files without executing new sweeps.
- Aggregate by hypothesis and family across runs, venues, symbols, exits,
  filters, and holding periods.
- Write compact JSON and Parquet artifacts:
  - `sandbox_global_leaderboard.json`;
  - `sandbox_global_leaderboard.parquet`.
- Include tested venues/symbols/exits/filters, run counts, result counts,
  status counts, best trial metrics, evidence-request trial IDs, blocker/reject
  reason counts, and a sandbox-only leaderboard decision.
- Add a research CLI command `rank-rapid-strategy-sandbox-artifacts` with
  research-root `--root-dir` and optional `--output-dir` enforcement.
- Register the command as research-owned and add boundary contract coverage.
- Add focused sandbox and live-boundary tests.
- Update sandbox docs and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-240-sandbox-global-leaderboard.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_LEADERBOARD_REPORT.md`
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

- The leaderboard finds multiple sandbox run manifests under a root and
  aggregates their rankings by hypothesis/family.
- Source manifests, rankings, and evidence-request descriptors are validated
  for sandbox boundary flags before aggregation.
- Leaderboard rows carry `research_only`, `observe_only`,
  `promotion_ready: false`, `sandbox_only`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- Decisions distinguish strict-validation-requested, screened-positive without
  request, mixed/inconclusive, falsified, and blocked hypotheses.
- The CLI rejects `--root-dir` or `--output-dir` outside the configured
  research output root.
- The CLI command is listed in the research command registry and boundary
  contract.
- Validation includes focused sandbox tests, CLI boundary tests,
  import-boundary tests, package compile, and the contract baseline when the
  local validation environment allows pytest-asyncio socket setup.

## Boundary

This packet summarizes existing sandbox run artifacts only. It does not execute
sandbox runs, execute strict validation, write candidate packs, create
paper/live signals, define sizing, place orders, mutate runtime mode, write
live configuration, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. The packet added read-only global sandbox
leaderboard generation, source run manifest/rankings/evidence-request boundary
validation, cross-run hypothesis/family aggregation, JSON/Parquet leaderboard
artifacts, `rank-rapid-strategy-sandbox-artifacts` CLI wiring,
research-command registry coverage, boundary-contract coverage, sandbox
contract coverage, artifact-catalog discovery for leaderboard reports, and
focused tests for cross-run aggregation, source boundary rejection, CLI
execution, catalog indexing, and research-root path rejection.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final focused results were 55 sandbox tests passed, 16 CLI boundary tests
passed, 11 import-boundary tests passed, and package compileall passed. The
full contract baseline was attempted and reached 460 passed tests before
failing during pytest-asyncio event-loop socketpair setup for one async
contract test with Windows `WinError 10055`, before the test body ran.
`ISSUE-R106-026` tracks this local validation-environment blocker.
