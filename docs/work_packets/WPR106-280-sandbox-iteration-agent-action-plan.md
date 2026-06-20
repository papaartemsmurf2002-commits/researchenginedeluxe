# WPR106-280 Sandbox Iteration Agent Action Plan

Status: closed
Owner: Codex Research Agent
Created: 2026-06-19

## Objective

Make sandbox iteration indexes expose one deterministic global action plan so
agents can start from the highest-priority repair or review item without
manually reconciling every action queue.

## Scope

- Add a read-only `agent_action_plan` to sandbox iteration index payloads.
- Derive action-plan items only from existing index rows and
  `recommended_actions`.
- Include deterministic priority, source queue labels, blocker/request context,
  counts, and key artifact/source paths for each action-plan item.
- Add action-plan counts, truncation metadata, and summary rollups.
- Preserve all existing action queues, queue ordering, recommended-action
  fields, artifact availability diagnostics, and boundary metadata.
- Add focused sandbox tests for request/preflight, archive-window, artifact
  repair, and missing-brief action-plan behavior.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-280-sandbox-iteration-agent-action-plan.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_AGENT_ACTION_PLAN_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration_index.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Index payloads include `agent_action_plan_version`,
  `agent_action_plan_limit`, `agent_action_plan_count`,
  `agent_action_plan_truncated_count`, `agent_action_plan_summary`, and
  `agent_action_plan`.
- Action-plan items keep sandbox boundary flags and include deterministic
  action priority, action rank, primary-action status, source queues, counts,
  blockers, validation descriptors, missing artifact keys, and relevant paths.
- Rows with multiple recommended actions expose dependent later actions with a
  `blocked_by_prior_action` marker.
- Action-plan summaries aggregate all matched action items, not only visible
  items.
- Existing action queue membership and summaries remain stable.
- The index remains read-only: it must not open child artifacts for validation,
  mutate artifacts, execute sandbox sweeps, execute strict validation, or write
  candidate artifacts.
- Validation includes focused sandbox tests, full sandbox tests, package
  compile, import-boundary tests, and the contract baseline when the local
  environment allows it.

## Boundary

This packet only adds a deterministic navigation plan to sandbox iteration
indexes. It does not download provider data, execute sandbox sweeps beyond
tests, execute strict validation, write candidate artifacts, create paper/live
signals, define sizing, place orders, mutate runtime mode, write live
configuration, mutate source archive files, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-19. Sandbox iteration indexes now emit
`agent_action_plan` plus version, limit, matched count, truncated count, and
summary metadata. Plan items are derived from row `recommended_actions` and
include deterministic priorities, source queue labels, context counts, paths,
and `blocked_by_prior_action` markers for dependent actions.

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
