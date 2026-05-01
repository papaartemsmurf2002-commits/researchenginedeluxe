# Work Packet: WP1-01-repo-inventory

Stage: Stage 1 - Repo cartography
Owner agent: Repo Cartographer Agent
Reviewer agent: Orchestrator Agent
Branch: `research/v3-experimental-engine`
Allowed paths:

- `docs/repo_cartography/REPO_INVENTORY.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_1_EXIT_REPORT.md`

Forbidden paths:

- `src/**`
- `tests/**`
- `configs/**`
- generated data, secrets, databases, logs, caches, and local artifacts

## Objective

Map the research branch without changing behavior.

## Required source files to read first

- `C:/Users/papaa/Downloads/AGENTIC_DEVELOPMENT_PLAN_TRADINGBOTSUITE.md`
- `README.md`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/**`
- `src/tradingbotsuite/adapters/execution.py`
- `src/tradingbotsuite/core/engine.py`

## Implementation tasks

- Record package and file-family inventory.
- Record import and boundary risks.
- List root launchers.
- List live order and execution paths.
- List research commands and artifact-producing paths.
- List tests that cover current research infrastructure.

## Tests and validation commands

```powershell
git grep -n "subparsers.add_parser" research/v3-experimental-engine -- src/tradingbotsuite/main.py src/tradingbot/cli.py
git grep -n "tradingbotsuite.adapters.execution\|HyperliquidExecution\|place_order" research/v3-experimental-engine -- src tests
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_feature_alignment.py tests/tradingbotsuite/test_experiment_runner.py -q
```

## Acceptance evidence

- `docs/repo_cartography/REPO_INVENTORY.md`
- `docs/stage_reports/STAGE_1_EXIT_REPORT.md`

## Handoff notes

The research branch has strong research assets, but live-adjacent runtime paths remain present. Later stages must separate contracts before promotion work.
