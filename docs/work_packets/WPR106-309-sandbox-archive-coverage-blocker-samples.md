# WPR106-309 Sandbox Archive Coverage Blocker Samples

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Expose bounded archive-coverage blocker samples in one-command iteration
manifests, agent briefs, and iteration-index queues so agents can identify the
blocked venue/archive descriptor groups directly from handoff artifacts without
reopening coverage matrices or source audits.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-309-sandbox-archive-coverage-blocker-samples.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_COVERAGE_BLOCKER_SAMPLES_REPORT.md`
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
  configuration, download provider data, mutate archive manifests/source files,
  or claim promotion readiness.
- Treat archive-coverage blocker samples as descriptor navigation metadata
  only.
- Derive samples only from already-produced archive coverage matrix rows.
- Keep samples bounded and deterministic.
- Do not alter archive audit semantics, archive coverage readiness semantics,
  venue descriptors, sweep execution, preflight trial estimates, ranking math,
  blocker semantics, evidence-request selection, trial IDs, or 2024+ window
  policy.

## Plan

1. Add bounded archive-coverage blocker samples and truncation metadata to
   one-command iteration manifest fields and agent briefs.
2. Project those samples into iteration-index rows, archive-window/preflight
   queue items, recommended archive-window action details, and agent-action-plan
   items.
3. Add focused regressions proving archive window repair handoffs carry
   descriptor IDs, blocker reasons, and requested-window evidence.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after confirming archive coverage rows carry
  blocked descriptor IDs and window/blocker counts, but one-command handoffs
  expose only aggregate blocker counts and top display summaries.
- 2026-06-19: Added bounded archive-coverage blocker samples and truncation
  metadata to one-command iteration manifests and agent briefs.
- 2026-06-19: Projected blocker samples into iteration-index rows,
  archive-window/preflight queue items, recommended archive-window action
  details, and global agent action-plan items.
- 2026-06-19: Bumped the iteration action queue schema to version 10 because
  queue and action-plan payloads now include archive coverage blocker samples.
- 2026-06-19: Added focused archive-window repair regression coverage for
  descriptor IDs, source paths, blocker reasons, and requested-window evidence.

## Completion Notes

Implemented and closed on 2026-06-19. One-command sandbox iteration manifests
and agent briefs now include bounded archive-coverage blocker samples derived
from existing coverage matrix rows. Iteration-index rows, archive-window and
preflight queue items, recommended archive-window action details, and global
agent action-plan items carry the same samples.

The action queue schema version is now 10.

This is descriptor navigation metadata only. The packet did not alter archive
audit semantics, archive coverage readiness semantics, venue archive
descriptors, sweep execution, preflight trial estimates, trial metrics,
rankings, blocker semantics, evidence-request selection, archive routing,
strict validation behavior, candidate-pack behavior, live/paper signal state,
sizing, order placement, runtime mode, live configuration, provider access,
archive manifests/source files, or promotion state.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "archive_window_repairs or action_queue_rollups or filters_archive_roots_to_resolved_window"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 3 focused archive-window/archive-sample/queue tests passed, 4
focused iteration-index tests passed, 170 sandbox tests passed, package
compileall passed, 11 import-boundary tests passed, and 461 contract tests
passed.
