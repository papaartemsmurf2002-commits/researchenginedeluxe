# Stage R106 Sandbox Archive Coverage Blocker Samples Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-309-sandbox-archive-coverage-blocker-samples.md`

## Summary

WPR106-309 surfaces compact archive-coverage blocker samples in one-command
sandbox iteration handoff artifacts. Archive coverage matrices already carried
blocked descriptor IDs and window/blocker evidence, but agents had to reopen
the coverage matrix or source audit to identify the blocked descriptor group.
Iteration manifests, agent briefs, iteration-index rows, queue items,
recommended action details, and agent action-plan rows now carry bounded
coverage blocker samples.

The action queue schema version is now 10.

## Implementation

- Added bounded archive-coverage blocker samples and truncation metadata to
  one-command iteration manifest fields and agent briefs.
- Each sample includes coverage key, venue, symbol, data family, interval,
  status, blocked/ready descriptor counts, bounded blocked descriptor IDs,
  bounded source paths, routing modes, blocker reason counts, requested-window
  bounds, requested-window row counts, observed/declarative window bounds, and
  market timestamp bounds.
- Iteration indexes now project samples into rows, archive-window/preflight
  queue items, recommended archive-window action details, and agent action-plan
  items.
- Focused regressions prove archive-window repair handoffs carry descriptor
  IDs, source paths, blocker reasons, and requested-window evidence.

## Boundary

This is descriptor navigation metadata only. The packet did not execute strict
validation, write candidate packs, create paper/live signals, define sizing,
place orders, change runtime mode, write live configuration, download provider
data, mutate archive manifests or source files, or claim promotion readiness.

The packet did not alter archive audit semantics, archive coverage readiness
semantics, venue archive descriptors, sweep execution, preflight trial
estimates, ranking math, blocker semantics, evidence-request selection, archive
routing, or trial IDs.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "archive_window_repairs or action_queue_rollups or filters_archive_roots_to_resolved_window"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 3 focused archive-window/archive-sample/queue tests passed.
- 4 focused iteration-index tests passed.
- 170 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
