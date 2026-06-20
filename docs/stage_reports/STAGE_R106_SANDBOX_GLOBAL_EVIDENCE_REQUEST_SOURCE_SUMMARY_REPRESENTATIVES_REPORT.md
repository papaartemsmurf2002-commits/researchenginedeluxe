# Stage R106 Sandbox Global Evidence-Request Source Summary Representatives Report

Date: 2026-06-19
Owner: Codex Research Agent
Packet: `docs/work_packets/WPR106-350-sandbox-global-evidence-request-source-summary-representatives.md`

## Summary

WPR106-350 enriches
`sandbox_artifact_catalog_global_evidence_request_source_summary.parquet` with
bounded representative evidence-request trial IDs, source trial IDs, source
request IDs, source artifact paths, and source leaderboard JSON paths per
source-context field/value row.

The sidecar remains compact descriptor navigation metadata. Agents can jump
from source venue, symbol, data family, interval, routing mode, venue
descriptor, or data-path coverage rows to concrete descriptor-only
strict-validation request rows without opening bucket representative sidecars
or scanning the full flat global evidence-request sidecar first.

## Boundary

- Source summary representative fields are derived from the in-memory global
  evidence-request rows already produced during the same catalog write.
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
