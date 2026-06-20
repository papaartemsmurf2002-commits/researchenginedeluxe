# Stage R106 Sandbox Artifact Catalog Agent Navigation Index Report

Date: 2026-06-19
Packet: `docs/work_packets/WPR106-353-sandbox-artifact-catalog-agent-navigation-index.md`
Status: closed

## Summary

WPR106-353 adds deterministic agent navigation metadata to sandbox artifact
catalog sidecar-index rows:

- `agent_read_order`
- `agent_read_group`
- `agent_first_read`
- `agent_navigation_hint`

The first-read sidecars are:

- `artifact_catalog`
- `global_evidence_request_source_priority_queue`
- `global_evidence_request_priority_queue`
- `strict_validation_descriptor_queue`
- `iteration_agent_action_plan`
- `replay_batch_plan_bucket_queue`

This lets agents discover the fastest read path for catalog, source-priority,
strict-validation, iteration-action, and replay-planning triage directly from
the sidecar index instead of relying on packet history or hard-coded filename
order.

## Boundary

The packet adds read-only catalog navigation metadata only. It does not change
sidecar row counts, sidecar payload schemas outside the sidecar index, artifact
discovery, sandbox scoring, ranking math, falsification decisions,
evidence-request selection, trial IDs, archive routing, source-integrity
behavior, preflight behavior, replay readiness, strict validation behavior,
candidate-pack state, or promotion state.

No sandbox sweep, iteration replay command, strict validation, provider
download, candidate-pack write, paper/live signal generation, sizing, order
placement, runtime-mode change, live configuration write, strategy-catalog
mutation, archive manifest/source mutation, or promotion claim was made.

## Validation

- Passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "artifact_catalog"`
  - 2 passed, 172 deselected.
- Passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`
  - 174 passed.
- Passed:
  `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`
- Passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q`
  - 11 passed.
- Passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - 461 passed.
- Passed:
  `git diff --check`
  - No whitespace errors; existing LF-to-CRLF warnings were reported.
- Passed:
  direct trailing-whitespace scan of packet-touched files.
