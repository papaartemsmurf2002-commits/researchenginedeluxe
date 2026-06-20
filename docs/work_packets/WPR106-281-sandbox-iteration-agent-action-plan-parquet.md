# WPR106-281 Sandbox Iteration Agent Action Plan Parquet

Status: closed
Owner: Codex Research Agent
Created: 2026-06-19

## Objective

Make the sandbox iteration `agent_action_plan` queryable as a compact Parquet
artifact so agents and batch tools can filter prioritized repair/request work
without parsing nested index JSON.

## Scope

- Add a deterministic `sandbox_iteration_agent_action_plan.parquet` output
  alongside `sandbox_iteration_index.json` and `sandbox_iteration_index.parquet`.
- Include `agent_action_plan_parquet_path` in index payloads when reports are
  written.
- Serialize action-plan items with existing sandbox boundary fields and JSON
  encoding for nested list/dict fields.
- Preserve existing index JSON payload shape, iteration-row Parquet output,
  action queues, action-plan ordering, and read-only behavior.
- Add focused sandbox tests proving the action-plan Parquet exists, has one
  row per visible action-plan item, preserves source queues and boundary flags,
  and is absent from payload paths when `write_report=False`.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-281-sandbox-iteration-agent-action-plan-parquet.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_AGENT_ACTION_PLAN_PARQUET_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration_index.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- `build_sandbox_iteration_index(..., write_report=True)` writes
  `sandbox_iteration_agent_action_plan.parquet`.
- The payload includes `agent_action_plan_parquet_path` when written and `None`
  when `write_report=False`.
- The Parquet row count equals the visible `agent_action_plan` item count.
- Boundary columns remain research-only, observe-only, non-promotable, and
  candidate-pack ineligible.
- Existing index JSON, iteration-row Parquet, action queues, and action-plan
  ordering remain stable.
- The export remains read-only: it must not open child artifacts for
  validation, mutate artifacts, execute sandbox sweeps, execute strict
  validation, or write candidate artifacts.
- Validation includes focused sandbox tests, full sandbox tests, package
  compile, import-boundary tests, and the contract baseline when the local
  environment allows it.

## Boundary

This packet only adds a queryable Parquet export for existing sandbox iteration
action-plan items. It does not download provider data, execute sandbox sweeps
beyond tests, execute strict validation, write candidate artifacts, create
paper/live signals, define sizing, place orders, mutate runtime mode, write
live configuration, mutate source archive files, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-19. Sandbox iteration indexes now write
`sandbox_iteration_agent_action_plan.parquet` when reports are enabled and
expose `agent_action_plan_parquet_path` in the index payload. The export
contains the visible action-plan items with sandbox boundary flags and JSON
encoded nested fields.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index or action_queue_rollups"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 5 focused iteration-index/action-queue tests passed, 115
sandbox tests passed, package compileall passed, 11 import-boundary tests
passed, and 461 contract tests passed.
