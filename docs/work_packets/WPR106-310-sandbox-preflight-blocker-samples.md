# WPR106-310 Sandbox Preflight Blocker Samples

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Expose bounded compatibility-preflight blocker samples in one-command
iteration manifests, agent briefs, and iteration-index queues so agents can
identify blocked strategy/archive combinations directly from handoff artifacts
without reopening full preflight Parquet or JSON rows.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-310-sandbox-preflight-blocker-samples.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_PREFLIGHT_BLOCKER_SAMPLES_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration.py`
- `src/tradingbotsuite/research_sandbox/iteration_index.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not execute strict validation, write candidate packs, create paper/live
  signals, define sizing, place orders, change runtime mode, write live
  configuration, download provider data, mutate strategy catalogs, mutate
  archive manifests/source files, or claim promotion readiness.
- Treat preflight blocker samples as descriptor navigation metadata only.
- Derive samples only from already-produced compatibility preflight rows.
- Keep samples bounded and deterministic.
- Do not alter compatibility-preflight blocker semantics, trial estimates,
  strategy rows, venue descriptors, sweep execution, ranking math,
  evidence-request selection, trial IDs, or 2024+ window policy.

## Plan

1. Add bounded preflight blocker samples and truncation metadata to
   one-command iteration manifest fields and agent briefs.
2. Project those samples into iteration-index rows, preflight repair queue
   items, recommended preflight action details, and agent-action-plan items.
3. Add focused regressions proving blocked strategy/archive combinations carry
   descriptor IDs, hypothesis IDs, signal columns, source paths, blocker
   reasons, and trial estimates through the handoff path.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after confirming compatibility preflight rows
  contain the blocked strategy/archive combination details, while one-command
  handoffs expose only aggregate preflight blocker counts and top display
  summaries.
- 2026-06-19: Added bounded preflight blocker samples and truncation metadata
  to one-command iteration manifests and agent briefs.
- 2026-06-19: Projected preflight blocker samples into iteration-index rows,
  preflight repair queue items, recommended preflight action details, and
  global agent action-plan items.
- 2026-06-19: Bumped the iteration action queue schema to version 11 because
  queue and action-plan payloads now include preflight blocker samples.
- 2026-06-19: Added focused regressions for blocked one-command preflight
  handoffs and iteration-index propagation.

## Completion Notes

Implemented and closed on 2026-06-19. One-command sandbox iteration manifests
and agent briefs now include bounded compatibility-preflight blocker samples
derived from existing preflight rows. Iteration-index rows, preflight repair
queue items, recommended preflight action details, and global agent action-plan
items carry the same samples.

The action queue schema version is now 11.

This is descriptor navigation metadata only. The packet did not alter
compatibility-preflight blocker semantics, trial estimates, strategy rows,
venue descriptors, sweep execution, ranking math, evidence-request selection,
trial IDs, archive routing, strict validation behavior, candidate-pack
behavior, live/paper signal state, sizing, order placement, runtime mode, live
configuration, provider access, strategy catalogs, archive manifests/source
files, or promotion state.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "skips_downstream_when_preflight_blocks_all_trials or summarizes_agent_iterations_and_briefs or action_queue_rollups"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 3 focused preflight/index/queue tests passed, 4 focused
iteration-index tests passed, 170 sandbox tests passed, package compileall
passed, 11 import-boundary tests passed, and 461 contract tests passed.
