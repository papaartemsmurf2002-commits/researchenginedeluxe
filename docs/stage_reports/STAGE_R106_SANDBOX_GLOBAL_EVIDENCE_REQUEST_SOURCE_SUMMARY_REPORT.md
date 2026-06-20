# Stage R106 Sandbox Global Evidence-Request Source Summary Report

Date: 2026-06-19
Owner: Codex Research Agent
Packet: `docs/work_packets/WPR106-347-sandbox-global-evidence-request-source-summary.md`

## Summary

WPR106-347 adds compact source-context count maps to the sandbox artifact
catalog global evidence-request summary and top-level catalog manifest fields.
The summary now exposes source venue, source symbol, source data family, source
interval, source routing mode, source venue descriptor, and source data-path
counts.

These maps are derived from the same in-memory global evidence-request rows
used to write flat request, priority queue, bucket queue, and representative
sidecars. They let agents decide which source-context queues are worth opening
before scanning the larger bucket or request sidecars.

## Boundary

- Source summaries are read-only descriptor navigation metadata derived only
  from in-memory global evidence-request rows produced during the same catalog
  write.
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
