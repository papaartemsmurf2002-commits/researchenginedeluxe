# Stage 1 Exit Report

Stage: Stage 1 - Repo cartography
Branch: `research/v3-experimental-engine`
Decision: complete
Date: 2026-05-01
Orchestrator: Codex

## Completed work packets

- WP1-01-repo-inventory
- WP1-02-tradingview-archive-map

## Validation commands run

```powershell
git ls-tree -r --name-only research/v3-experimental-engine
git grep -n "subparsers.add_parser" research/v3-experimental-engine -- src/tradingbotsuite/main.py src/tradingbot/cli.py
git grep -n "tradingbotsuite.adapters.execution\|HyperliquidExecution\|place_order" research/v3-experimental-engine -- src tests
git grep -n "TradingView\|Pine\|parity\|tv_\|lorentz_tv\|features_tv\|kernels_tv\|lc_marker" research/v3-experimental-engine -- .
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_feature_alignment.py tests/tradingbotsuite/test_experiment_runner.py tests/test_removed_source_boundaries.py -q
```

## Results

- File inventory: 253 tracked files; 74 under `src/**`; 33 under `tests/**`; 127 under `docs/**`.
- Research commands, live order paths, root launchers, import risks, and tests were mapped.
- TradingView/Pine/parity active surfaces were confirmed removed from the research branch command surface; remaining references are documented as historical or contract naming.
- `python -m compileall -q src/tradingbotsuite`: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_feature_alignment.py tests/tradingbotsuite/test_experiment_runner.py tests/test_removed_source_boundaries.py -q`: passed, 10 tests.

## Artifacts produced

- `docs/repo_cartography/REPO_INVENTORY.md`
- `docs/repo_cartography/TRADINGVIEW_ARCHIVE_MAP.md`
- `docs/work_packets/WP1-01-repo-inventory.md`
- `docs/work_packets/WP1-02-tradingview-archive-map.md`
- `docs/stage_reports/STAGE_1_EXIT_REPORT.md`

## Known issues

- ISSUE-R1-001: Research branch still contains live execution surfaces.
- ISSUE-R1-002: Research CLI and live/operator CLI are coupled in one entry module.

## Carry-forward debt

- Stage 2 must define enforceable data, feature, strategy, backtest, artifact, promotion, and import-boundary contracts.
- Stage 10 must reject live-mode research jobs and research-only artifacts on the live branch.

## Decision rationale

Stage 1 is complete because cartography is documented and no P0 issue is open. The two open P1 risks are below the stop-rule threshold and are assigned to later contract and live-hardening stages.
