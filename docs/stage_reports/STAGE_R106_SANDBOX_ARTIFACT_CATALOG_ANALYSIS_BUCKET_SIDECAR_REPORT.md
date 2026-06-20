# Stage R106 Sandbox Artifact Catalog Analysis Bucket Sidecar Report

Date: 2026-06-19
Packet: WPR106-335
Owner: Codex Research Agent

## Summary

WPR106-335 adds
`sandbox_artifact_catalog_analysis_bucket_rollups.parquet` to sandbox artifact
catalog outputs. The sidecar flattens already-written run analysis bucket
rollups across cataloged `analysis_summary.json` files so agents can query
venue, family, exit, filter, and venue/family buckets across many sandbox runs
without opening each JSON report.

The sidecar rows include source analysis paths, source run IDs, bucket identity,
status and result counts, positive-net counts, evidence-request counts, best
representative trial fields, and explicit non-authorizing flags. The sidecar is
also registered in the catalog sidecar index with post-write existence,
byte-size, and SHA-256 metadata.

## Boundary

- The sidecar is derived only from already-loaded `analysis_summary.json`
  payloads and embedded bounded bucket rollups.
- No ranking Parquet metrics are recomputed and no evidence-request selection,
  scoring, ranking, trial IDs, archive routing, preflight behavior, or
  falsification decision is changed.
- No sandbox sweep, replay command, strict validation, provider download,
  candidate-pack write, paper/live signal, sizing instruction, order
  instruction, runtime-mode change, live configuration write, strategy catalog
  mutation, archive manifest/source mutation, or promotion claim was created by
  this packet.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "artifact_catalog_indexes_known_artifacts or artifact_catalog_surfaces_failed_run_integrity"`
  passed with 2 passed and 172 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`
  passed with 174 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q`
  passed with 11 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  passed with 461 passed.

## Result

The artifact catalog now exposes cross-run analysis-bucket triage as a compact
Parquet sidecar with stable empty-schema behavior and sidecar file identity,
while preserving research-only, observe-only, sandbox-only,
promotion-ready-false outputs.
