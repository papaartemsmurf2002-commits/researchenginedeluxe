# WPR80-01 Operator Discovery UI

Status: in_progress
Owner: Codex Research Agent
Stage: R80 operator discovery UI

## Objective

Expose V4 discovery runs and discovery artifacts in the operator Research tab without changing discovery math, historical-cycle semantics, candidate-pack gates, promotion behavior, or live execution. The UI must queue discovery runs through the same research-job guardrails as existing operator jobs, keep all outputs under the configured research output directory, and make run state, snapshots, candidate ledgers, and blockers visible.

## Allowed paths

- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_operator_ui.py`
- `docs/work_packets/WPR80-01-operator-discovery-ui.md`
- `docs/stage_reports/STAGE_R80_OPERATOR_DISCOVERY_UI_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`

## Non-goals

- Do not alter checked BTCUSDT or ETHUSDT historical-cycle configs.
- Do not change discovery feature math, HMM/KNN materialization, KNN search, ablation, exit-lab, optimizer, backtest, candidate-pack, promotion, or live behavior.
- Do not mark any discovery output as promotable or live-ready.
- Do not add live order-placement imports to research or discovery modules.

## Implementation plan

1. Add a guarded operator job for discovery runs that accepts checked `configs/discovery` specs or specs under the configured research output root.
2. Keep discovery job outputs isolated under `research_output_dir/operator_runs/discovery_runs/<run_id>` by rewriting the queued spec before execution, so resume can target the same paused run without overwriting checked evidence.
3. Support resume and bounded stop-after-trials controls for safe pause/resume workflows.
4. Extend artifact scanning with a `discovery_run` summary covering run state, snapshots, candidate ledgers, blocker counts, and research-only boundary flags.
5. Add dense Research-tab controls/cards/charts for discovery launch and artifact review using existing template conventions.
6. Add focused operator UI/API/job tests and run validation.

## Validation target

- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
