# Stage R106 Sandbox Iteration Venue Expansion Gap Handoff Report

Date: 2026-06-19
Packet: `WPR106-355-sandbox-iteration-venue-expansion-gap-handoff`

## Summary

WPR106-355 surfaces the WPR106-354 venue-expansion archive coverage sidecar in
one-command sandbox iteration handoff artifacts. Iteration manifests, agent
briefs, iteration index rows, action queues, and agent action-plan rows now
carry the venue-expansion sidecar path, target venue list, status/action counts,
actionable gap counts, and bounded samples for OKX, Bybit, and Hyperliquid
archive descriptor repair/addition.

## Implementation

- Added compact actionable venue-expansion gap samples to sandbox iteration
  manifests from already-produced archive coverage rows.
- Added `archive_coverage_venue_expansion_gaps_parquet_path` to iteration
  artifact paths and cached artifact checks when referenced.
- Added venue-expansion counts and samples to sandbox agent briefs.
- Added iteration-index fields for venue-expansion target venues, status/action
  counts, actionable counts, bounded samples, and sidecar paths.
- Added `venue_expansion_gap_queue` and descriptor-only
  `repair_or_add_venue_expansion_archives` agent action.
- Preserved rejection-review actions as secondary actions when sandbox
  rejections exist and no strict-validation requests are pending.

## Boundary

The handoff is diagnostic only. It does not add archive descriptors, mutate
venue archive manifests or source files, download venue data, execute strict
validation, write candidate packs, change replay readiness, change scoring,
change trial IDs, change promotion flags, or authorize live/paper behavior.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index"`:
  4 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "agent_iteration or archive_coverage or action_queue_rollups or input_replay"`:
  30 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`:
  174 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q`:
  11 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`: 461 passed.
- `git diff --check`: passed with existing LF-to-CRLF warnings only.
- Direct trailing-whitespace scan of packet-touched files: passed.
