# Stage R106 Sandbox Global Evidence-Request Source Summary Sidecar Report

Date: 2026-06-19
Owner: Codex Research Agent
Packet: `docs/work_packets/WPR106-348-sandbox-global-evidence-request-source-summary-sidecar.md`

## Summary

WPR106-348 writes
`sandbox_artifact_catalog_global_evidence_request_source_summary.parquet`, a
compact descriptor-only sidecar flattened from the in-memory global
evidence-request source summary. The sidecar emits one row per non-empty
source-context field/value count for source venue, source symbol, source data
family, source interval, source routing mode, source venue descriptor, and
source data path.

The sidecar is registered in the catalog sidecar index with row count, empty
status, file existence, byte size, and SHA-256 identity. Catalog payloads also
expose the sidecar path and row count so agents can query source availability
without opening the catalog JSON or full flat request sidecar.

## Boundary

- Source summary sidecar rows are read-only descriptor navigation metadata
  derived only from the in-memory global evidence-request summary produced
  during the same catalog write.
- The catalog writer does not open per-run evidence request files, open or
  recompute the full global leaderboard Parquet, execute strict validation, or
  authorize validation.
- Existing leaderboard scoring, ranking, falsification decisions,
  evidence-request selection, trial IDs, archive routing, source-integrity
  checks, 2024+ window filtering, and promotion state are unchanged.
- All rows remain research-only, observe-only, sandbox-only,
  candidate-pack-ineligible, descriptor-only where applicable, and
  promotion-ready false.
- No sandbox sweep, iteration replay command, provider download, strict-cycle
  execution, candidate-pack write, paper/live artifact, order, sizing,
  runtime-mode change, live configuration write, strategy-catalog mutation,
  archive manifest/source mutation, or promotion claim exists.

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
- Passed:
  `git diff --check`
  - No whitespace errors; existing LF-to-CRLF warnings were reported.
- Passed:
  direct trailing-whitespace scan of packet-touched files.
