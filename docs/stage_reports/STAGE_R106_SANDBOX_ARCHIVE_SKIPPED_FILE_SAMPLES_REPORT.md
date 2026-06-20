# Stage R106 Sandbox Archive Skipped File Samples Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-308-sandbox-archive-skipped-file-samples.md`

## Summary

WPR106-308 surfaces compact skipped archive-file context in one-command sandbox
iteration handoff artifacts. Archive-root materialization already wrote
skipped build-report rows, but agents had to reopen the full build report to
identify which local files were bad or outside the requested window. Iteration
manifests, agent briefs, iteration-index rows, queue items, recommended action
details, and agent action-plan rows now carry bounded skipped-file samples and
aggregate archive file counts.

The action queue schema version is now 9.

## Implementation

- Added archive-source summaries for built archive manifests with file
  status/suffix counts, skipped-file reason counts, bounded skipped-file
  samples, and truncation metadata.
- Each skipped-file sample includes source path, suffix, SHA-256, byte size,
  skip reasons, normalized row count, source window bounds, and requested
  window bounds.
- Agent briefs now include `archive_source_summary`.
- Iteration indexes now project archive-source summaries into rows, queue
  items, queue summaries, recommended archive-window action details, and agent
  action-plan items.
- Focused regressions cover real `outside_requested_window` archive-root skips
  and low-level queue/action-plan propagation under queue truncation.

## Boundary

This is descriptor navigation metadata only. The packet did not execute strict
validation, write candidate packs, create paper/live signals, define sizing,
place orders, change runtime mode, write live configuration, download provider
data, mutate archive source files, or claim promotion readiness.

The packet did not alter venue archive descriptors, archive coverage
semantics, sweep execution, preflight trial estimates, ranking math, blocker
semantics, evidence-request selection, archive routing, or trial IDs.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "filters_archive_roots_to_resolved_window or action_queue_rollups"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 2 focused archive-sample/queue tests passed.
- 4 focused iteration-index tests passed.
- 170 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
