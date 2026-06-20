# Stage R106 Sandbox Global Evidence-Request Source Buckets Report

Date: 2026-06-19
Owner: Codex Research Agent
Packet: `docs/work_packets/WPR106-346-sandbox-global-evidence-request-source-buckets.md`

## Summary

WPR106-346 extends sandbox artifact catalog global evidence-request bucket
queues and bucket representatives with source-context routing metadata. The
bucket queue can now group descriptor-only strict-validation requests by source
venue, source symbol, source venue/symbol, source data family, source interval,
source venue descriptor, source routing mode, and source data path.

Bucket queue rows expose the matching source-context fields for each
source-context bucket. Bucket representative rows expose both bucket-level
source-context fields and row-level source request context, including source
request IDs, source run paths, requested-validation labels, routing/data-path
metadata, compact source metrics, and source market/execution-assumption JSON
fields already available on the flattened request rows.

## Boundary

- Source buckets are read-only descriptor navigation metadata derived only from
  in-memory global evidence-request rows produced during the same catalog write.
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
