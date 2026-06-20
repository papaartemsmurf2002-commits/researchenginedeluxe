# WPR106-279 Sandbox Iteration Recommended Actions

Status: closed
Owner: Codex Research Agent
Created: 2026-06-19

## Objective

Make sandbox iteration action queues more directly usable by agents by adding
deterministic recommended action hints derived from existing index metadata.

## Scope

- Add read-only recommended action hints to iteration index rows.
- Include the same hints in action queue items.
- Add recommended-action rollups to action queue summaries and top-level index
  payloads.
- Keep hints deterministic and derived only from already-indexed counts,
  blockers, brief status, artifact availability, and descriptor-only request
  metadata.
- Bump the action queue schema version.
- Add focused sandbox tests for strict-validation request, preflight repair,
  archive-window repair, artifact repair, and missing-brief action hints.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-279-sandbox-iteration-recommended-actions.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_RECOMMENDED_ACTIONS_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration_index.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Iteration index rows include a compact `recommended_actions` list and primary
  `recommended_action`.
- Action queue items expose the same recommended actions.
- Queue summaries include `recommended_action_counts` aggregated from all
  matched rows, including rows hidden behind the visible queue limit.
- Top-level index payloads include `recommended_action_counts`.
- Existing queue membership, queue ordering, artifact availability diagnostics,
  source context fields, and boundary metadata remain stable.
- The index remains read-only: it must not open child artifacts for validation,
  mutate artifacts, execute sandbox sweeps, execute strict validation, or write
  candidate artifacts.
- Validation includes focused sandbox tests, full sandbox tests, package
  compile, import-boundary tests, and the contract baseline when the local
  environment allows it.

## Boundary

This packet only adds deterministic navigation hints to sandbox iteration
indexes and queues. It does not download provider data, execute sandbox sweeps
beyond tests, execute strict validation, write candidate artifacts, create
paper/live signals, define sizing, place orders, mutate runtime mode, write
live configuration, mutate source archive files, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-19. Sandbox iteration index rows and action
queue items now include `recommended_action` plus detailed
`recommended_actions`; queue summaries and top-level payloads include
recommended-action rollups. The action queue schema version is now 6.

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
