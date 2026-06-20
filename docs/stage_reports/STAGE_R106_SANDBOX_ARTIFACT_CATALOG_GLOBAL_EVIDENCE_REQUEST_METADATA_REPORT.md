# Stage R106 Sandbox Artifact Catalog Global Evidence-Request Metadata Report

Date: 2026-06-19
Owner: Codex Research Agent
Packet: `docs/work_packets/WPR106-343-sandbox-artifact-catalog-global-evidence-request-metadata.md`

## Summary

WPR106-343 adds compact global evidence-request metadata to sandbox artifact
catalog outputs. Global leaderboard catalog rows now expose request counts,
unique request-trial counts, requesting-hypothesis counts,
requested-validation count maps, leaderboard-decision count maps, family count
maps, and tested venue/symbol count maps derived only from bounded
`top_hypotheses` already present in loaded `sandbox_global_leaderboard.json`
payloads.

The catalog manifest now also exposes a `global_evidence_request_summary`
derived from in-memory global evidence-request rows, bucket queues, and
representative rows produced during the same catalog write. That summary gives
agents request, bucket, and representative counts before they open any
evidence-request sidecar.

## Boundary

- Row metadata is derived only from loaded global leaderboard JSON preview rows.
- Manifest summary metadata is derived only from in-memory request rows, bucket
  queues, and representative rows already built during the same catalog write.
- The catalog writer does not open or recompute the full
  `sandbox_global_leaderboard.parquet` companion file for this metadata.
- The metadata is descriptor-only routing context. It does not execute or
  authorize strict validation.
- No sandbox scoring, ranking math, falsification decision, blocker/rejection
  semantics, evidence-request selection, trial ID, archive routing, preflight
  behavior, source-integrity behavior, replay readiness, or promotion state was
  changed.
- No candidate pack, paper/live artifact, order, sizing, runtime-mode change,
  live configuration write, provider download, strict-cycle execution, strategy
  catalog mutation, archive manifest/source mutation, replay command execution,
  validation execution, or promotion claim exists.

## Validation

- Passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "global_leaderboard or artifact_catalog"`
  - 4 passed, 170 deselected.
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
