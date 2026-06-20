# Stage R106 Sandbox Next-Action Dashboard Report

Date: 2026-06-20
Packet: `WPR106-371-sandbox-next-action-dashboard`

## Summary

WPR106-371 adds a first-read next-action dashboard for the rapid strategy
sandbox. The new `show-rapid-strategy-sandbox-next-action` command reads
existing sandbox artifact catalog and iteration index JSON files under the
configured research output root, or discovers matching files under that root,
then writes a compact `sandbox_next_action_report.json` and
`sandbox_next_action_report.parquet`.

The report summarizes iteration status, action queue counts, blockers, missing
venue coverage, descriptor-only strict-validation queues, venue-expansion
requests, artifact warnings, best-hypothesis sidecar pointers, the next
recommended packet type, and exact files to open next.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "next_action_dashboard"`
  - `2 passed, 186 deselected`
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  - `25 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `202 passed`
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `461 passed`
- `git diff --check`
  - passed with existing LF-to-CRLF warnings only

## Boundary Statement

The dashboard is read-only navigation metadata. It does not execute sandbox
sweeps, artifact indexers, strict-validation preflight, strict validation,
provider downloads, replay commands, candidate-pack writes, paper/live
behavior, sizing, order placement, runtime-mode changes, live config writes,
candidate-evidence claims, or promotion claims. Outputs remain research-only,
observe-only, sandbox-only, non-promotable, non-candidate-evidence, and
descriptor-only.
