# Work Packet: WP2-01-contract-docs

Stage: Stage 2 - Docs and contracts
Owner agent: Documentation Agent
Reviewer agent: Orchestrator Agent
Branch: `research/v3-experimental-engine`
Allowed paths:

- `AGENTS.md`
- `START_HERE.md`
- `docs/contracts/**`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/work_packets/WP2-01-contract-docs.md`
- `docs/stage_reports/STAGE_2_EXIT_REPORT.md`
- `tests/contracts/**`

Forbidden paths:

- production code under `src/**`
- generated data, secrets, databases, logs, caches, and local artifacts

## Objective

Create the Stage 2 contract baseline and the first import-boundary tests for the research branch.

## Required source files to read first

- `C:/Users/papaa/Downloads/AGENTIC_DEVELOPMENT_PLAN_TRADINGBOTSUITE.md`
- `docs/repo_cartography/REPO_INVENTORY.md`
- `docs/repo_cartography/TRADINGVIEW_ARCHIVE_MAP.md`
- `docs/KNOWN_ISSUES.md`

## Implementation tasks

- Add agent and start-here guidance.
- Add data, feature, strategy, backtest, artifact, promotion, and boundary contracts.
- Add contract tests for research import boundaries and required docs.
- Update the stage ledger, known issues, and exit report.

## Tests and validation commands

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts tests/test_removed_source_boundaries.py -q
```

## Acceptance evidence

- Contract docs exist.
- Boundary tests pass.
- Stage 2 exit report records validation.

## Handoff notes

Stage 3 data architecture may begin only after this work packet closes and the ledger says `Decision: advance`.
