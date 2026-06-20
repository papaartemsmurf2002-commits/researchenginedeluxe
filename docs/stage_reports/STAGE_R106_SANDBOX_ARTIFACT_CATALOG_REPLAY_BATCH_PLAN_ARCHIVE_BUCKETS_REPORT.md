# Stage R106 Sandbox Artifact Catalog Replay Batch-Plan Archive Buckets Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-320-sandbox-artifact-catalog-replay-batch-plan-archive-buckets.md`

## Summary

WPR106-320 projects descriptor-only input replay batch-plan archive bucket and
archive-window bucket count maps into sandbox artifact catalog rows, top-level
replay batch-plan summaries, and bounded replay batch-plan queue items. Agents
can now triage OKX/Bybit/Hyperliquid replay coverage from catalog artifacts
without reopening each batch-plan JSON.

## Boundary

The new fields are read-only artifact navigation metadata derived only from
already-loaded batch-plan JSON payloads and summaries. The packet does not
execute replay commands or validation, download provider data, run strict
cycles, mutate strategy catalogs, mutate archive manifests or source files,
write candidate packs, create paper/live artifacts, define sizing, place
orders, change runtime mode, write live configuration, or make promotion-ready
claims.

## Implementation

- Added catalog row fields for ready/planned archive bucket counts and
  ready/planned archive-window bucket counts.
- Aggregated those maps into `replay_batch_plan_summary` so catalog consumers
  can inspect multi-venue coverage at the manifest level.
- Included the same maps on bounded replay batch-plan queue items for fast
  agent handoff triage.
- Added regressions for duplicate-rich ready batch plans and blocked-only batch
  plans, covering row, summary, and queue projections.
- Updated the sandbox research contract and active index to document the
  read-only archive-bucket projection contract.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "input_replay"`:
  3 passed, 171 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "input_replay or iteration_index"`:
  7 passed, 167 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`:
  174 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`:
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q`:
  11 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`:
  461 passed.
