# Stage R106 Sandbox Source Discovery Bounds Report

Date: 2026-06-20
Packet: `WPR106-379-sandbox-source-discovery-bounds`

## Summary

WPR106-379 closes the post-audit M5 discovery-cost gap for the sandbox source
scanners. Strategy catalog materialization, archive manifest building, and
global leaderboard run discovery now use a shared deterministic bounded
traversal helper that sorts entries within each directory only and stops after
the configured source/run limit. The previous strategy/archive/leaderboard
paths could sort a full recursive tree before applying `max_files` or
`max_runs`.

The new helper preserves deterministic local first-N behavior, reports
truncation when an additional matching file is observed beyond the configured
limit, and does not change accepted source parsing, skipped-source repair rows,
archive descriptor semantics, leaderboard scoring, strict-validation handoff,
or sandbox boundary metadata.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -k "discovery_bound" -q`
  - `3 passed, 195 deselected`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `219 passed`
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  - `26 passed`

## Boundary Statement

This packet changes only local sandbox source discovery traversal. It does not
download provider data, mutate source catalogs or archives, alter sandbox sweep
semantics, execute strict validation, write candidate packs, create paper/live
signals, define sizing, place orders, change runtime mode, write live
configuration, claim candidate evidence, or authorize promotion.
