# Work Packet: WP0-01-branch-and-ledger-setup

Stage: Stage 0 - Governance and branches
Owner agent: Orchestrator Agent
Reviewer agent: QA Agent
Branch: `research/v3-experimental-engine`
Allowed paths:

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/BRANCH_PURPOSE.md`
- `docs/work_packets/WP0-01-branch-and-ledger-setup.md`
- `docs/stage_reports/STAGE_0_EXIT_REPORT.md`

Forbidden paths:

- `src/**`
- `tests/**`
- `configs/**`
- generated data, secrets, databases, logs, caches, and local artifacts

## Objective

Create the research branch governance baseline required before any implementation work.

## Required source files to read first

- `C:/Users/papaa/Downloads/AGENTIC_DEVELOPMENT_PLAN_TRADINGBOTSUITE.md`
- `README.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`

## Implementation tasks

- Create `research/v3-experimental-engine` from `codex/hmm-knn-research-package`.
- Create the orchestrator stage ledger.
- Create the known issues registry.
- Add branch-purpose documentation.
- Write the Stage 0 exit report.

## Tests and validation commands

```powershell
git branch --list research/v3-experimental-engine --verbose --no-abbrev
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_feature_alignment.py tests/tradingbotsuite/test_experiment_runner.py -q
```

## Acceptance evidence

- Branch exists locally and remotely.
- Governance documents exist on the branch.
- No open P0 or P1 issues are recorded.
- Validation command results are recorded in `docs/stage_reports/STAGE_0_EXIT_REPORT.md`.

## Handoff notes

Stage 1 should inventory research commands, provider/archive modules, feature-alignment contracts, artifact-producing experiment paths, legacy TradingView/parity files, root launchers, and forbidden live-order imports.
