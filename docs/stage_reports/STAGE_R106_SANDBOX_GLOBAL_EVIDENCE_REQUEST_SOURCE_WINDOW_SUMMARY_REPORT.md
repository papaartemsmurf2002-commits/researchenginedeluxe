# Stage R106 Sandbox Global Evidence-Request Source Window Summary Report

Date: 2026-06-19
Owner: Codex Research Agent
Packet: `docs/work_packets/WPR106-349-sandbox-global-evidence-request-source-window-summary.md`

## Summary

WPR106-349 enriches
`sandbox_artifact_catalog_global_evidence_request_source_summary.parquet` with
unique request-trial counts, source leaderboard counts, and source market
start/end min/max bounds per source-context field/value row.

The sidecar remains compact descriptor navigation metadata. Agents can verify
2024+ source coverage by source venue, symbol, data family, interval, routing
mode, venue descriptor, and data path without scanning the full flat global
evidence-request sidecar first.

## Boundary

- Source window summary fields are derived from the in-memory global
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
