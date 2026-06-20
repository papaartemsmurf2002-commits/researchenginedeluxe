# Stage R106 Sandbox Artifact Catalog Global Evidence-Request Priority Queue Report

Date: 2026-06-19
Owner: Codex Research Agent
Packet: `docs/work_packets/WPR106-344-sandbox-artifact-catalog-global-evidence-request-priority-queue.md`

## Summary

WPR106-344 adds
`sandbox_artifact_catalog_global_evidence_request_priority_queue.parquet` to
sandbox artifact catalog outputs. The sidecar is a bounded descriptor-only
queue of concrete global leaderboard evidence-request rows, sorted from the
in-memory global evidence-request sidecar rows by leaderboard rank, score,
source artifact, and stable evidence-request identity.

The queue exposes request/source trial IDs, requested validation, source
leaderboard paths, hypothesis/family context, tested venue/symbol context,
compact best-trial metrics, leaderboard decisions, reason-count maps, and
non-authorizing boundary flags. The catalog manifest exposes queue
limit/count/path/row-count fields and records the queue in
`global_evidence_request_summary`.

## Boundary

- Queue rows are derived only from in-memory global evidence-request rows
  generated from bounded global leaderboard JSON preview rows during the same
  catalog write.
- The catalog writer does not open or recompute the full
  `sandbox_global_leaderboard.parquet` companion file for this queue.
- The queue is descriptor-only routing metadata. It does not execute or
  authorize strict validation.
- Empty catalogs still write an empty-schema Parquet sidecar for stable
  automation.
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
