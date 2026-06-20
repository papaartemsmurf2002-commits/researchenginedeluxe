# WPR106-308 Sandbox Archive Skipped File Samples

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Expose bounded skipped archive-file samples in one-command iteration summaries
and iteration-index queues so agents can identify out-of-window or invalid
archive files directly from handoff artifacts without reopening full build
reports.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-308-sandbox-archive-skipped-file-samples.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_SKIPPED_FILE_SAMPLES_REPORT.md`
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
  configuration, download provider data, mutate archive source files, or claim
  promotion readiness.
- Treat skipped archive-file samples as descriptor navigation metadata only.
- Derive samples only from already-produced archive manifest build-report
  metadata.
- Keep samples bounded and deterministic.
- Do not alter venue archive descriptor rows, archive coverage semantics,
  sweep execution, preflight trial estimates, ranking math, blocker semantics,
  evidence-request selection, trial IDs, or 2024+ window policy.

## Plan

1. Add bounded skipped archive-file samples and truncation metadata to built
   archive-source summaries.
2. Surface those samples in iteration agent briefs, iteration-index rows,
   queue items, and agent-action-plan items.
3. Add focused regressions proving real archive-root skipped files and
   low-level queue/action-plan propagation carry the sample metadata.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after confirming archive manifest build reports
  include skipped file reasons, but iteration manifests and queues expose only
  skipped counts and report paths.
- 2026-06-19: Added compact archive-source summaries with file status/suffix
  counts, skipped-file reason counts, bounded skipped-file samples, and
  truncation metadata.
- 2026-06-19: Projected archive-source summaries into agent briefs,
  iteration-index rows, queue items, recommended archive-window action details,
  and global agent action-plan items.
- 2026-06-19: Bumped the iteration action queue schema to version 9 because
  queue item and action-plan payloads now include skipped archive-file context.
- 2026-06-19: Added focused regressions for real archive-root
  `outside_requested_window` skips and low-level queue/action-plan propagation.

## Completion Notes

Implemented and closed on 2026-06-19. One-command sandbox iteration
archive-source summaries now include file status/suffix counts, skipped-file
reason counts, bounded skipped archive-file samples, and truncation metadata.
Agent briefs, iteration-index rows, archive/preflight queue items, recommended
archive-window action details, and agent action-plan items carry the same
skipped-file context so agents can identify bad or out-of-window archive files
directly from handoff artifacts.

The action queue schema version is now 9.

This is descriptor navigation metadata only. The packet did not alter venue
archive descriptors, archive coverage semantics, sweep execution, preflight
trial estimates, trial metrics, rankings, blocker semantics, evidence-request
selection, archive routing, strict validation behavior, candidate-pack
behavior, live/paper signal state, sizing, order placement, runtime mode, live
configuration, provider access, archive source files, or promotion state.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "filters_archive_roots_to_resolved_window or action_queue_rollups"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 2 focused archive-sample/queue tests passed, 4 focused
iteration-index tests passed, 170 sandbox tests passed, package compileall
passed, 11 import-boundary tests passed, and 461 contract tests passed.
