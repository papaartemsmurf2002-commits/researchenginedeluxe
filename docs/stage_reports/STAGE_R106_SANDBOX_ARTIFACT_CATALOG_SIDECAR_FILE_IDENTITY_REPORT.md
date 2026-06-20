# Stage R106 Sandbox Artifact Catalog Sidecar File Identity Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-330-sandbox-artifact-catalog-sidecar-file-identity.md`

## Summary

WPR106-330 adds file identity metadata to sandbox artifact catalog sidecar index
rows. The catalog writer now records whether each companion sidecar file exists,
its byte size, and its SHA-256 digest after the companion catalog, replay
batch-plan, and strict-validation Parquet sidecars are written.

The sidecar index remains research-only navigation metadata. It does not index
itself, execute replay or validation commands, authorize strict validation,
write candidate packs, mutate source artifacts, or change any research decision.

## Implementation

- Extended the sidecar index Parquet schema with `sidecar_exists`,
  `sidecar_size_bytes`, and `sidecar_sha256`.
- Added post-write SHA-256 identity collection for catalog-written companion
  sidecars only.
- Recomputed sidecar index rows after companion sidecars are emitted and before
  writing the sidecar index Parquet and catalog JSON payload.
- Kept `write_report=False` descriptor behavior non-writing and
  non-authorizing.
- Added regression checks for populated sidecars and empty-schema sidecars
  produced when strict-validation queues are empty.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "artifact_catalog"`
  passed with 2 passed and 172 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`
  passed with 174 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q`
  passed with 11 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed with 461
  passed.

## Boundary

No candidate pack, paper/live artifact, order/sizing/runtime change, live config
write, provider download, strict-cycle execution, strategy catalog mutation,
archive manifest/source mutation, replay command execution, validation
execution, or promotion claim exists.
