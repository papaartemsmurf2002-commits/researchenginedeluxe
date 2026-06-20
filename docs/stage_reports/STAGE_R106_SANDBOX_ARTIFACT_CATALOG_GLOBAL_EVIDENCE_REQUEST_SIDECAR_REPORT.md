# Stage R106 Sandbox Artifact Catalog Global Evidence-Request Sidecar Report

Date: 2026-06-19
Owner: Codex Research Agent
Packet: `docs/work_packets/WPR106-340-sandbox-artifact-catalog-global-evidence-request-sidecar.md`

## Summary

WPR106-340 adds a catalog-owned
`sandbox_artifact_catalog_global_evidence_requests.parquet` sidecar. The
sidecar flattens bounded global leaderboard
`top_hypotheses[*].evidence_request_trial_ids` from already-loaded
`sandbox_global_leaderboard.json` payloads, then registers the sidecar in the
artifact catalog sidecar index with post-write file identity metadata.

The sidecar exposes source leaderboard paths, evidence request trial/source
IDs, requested-validation labels, hypothesis/family context, tested dimensions,
compact counts, decision labels, reason counts, and non-authorizing sandbox
boundary flags. Catalogs with no global evidence-request rows still write an
empty-schema Parquet file for stable automation.

## Boundary

- Rows are derived only from bounded `top_hypotheses` already present in loaded
  global leaderboard JSON payloads.
- The catalog writer does not open or recompute the full
  `sandbox_global_leaderboard.parquet` companion file for this sidecar.
- The sidecar is descriptor-only routing metadata. It does not execute or
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

