# Stage R106 Sandbox Global Leaderboard Evidence-Request Source Context Report

Date: 2026-06-19
Owner: Codex Research Agent
Packet: `docs/work_packets/WPR106-345-sandbox-global-leaderboard-evidence-request-source-context.md`

## Summary

WPR106-345 adds bounded evidence-request source-context previews to sandbox
global leaderboard top-hypothesis rows. The preview is derived only from
already-loaded per-run `evidence_requests.json` descriptors and is capped at 50
contexts per top hypothesis.

Artifact catalogs now preserve that context in flat global evidence-request
rows and the bounded global evidence-request priority queue. The flattened
fields include source request IDs, source run IDs/paths, requested-validation
labels, market start/end, routing/data-path/container metadata, compact source
metrics, and source market/execution-assumption JSON fields. Catalog manifests
also expose context availability and routing-count summaries.

## Boundary

- Source context is read-only descriptor metadata derived from already-loaded
  evidence-request payloads and bounded global leaderboard preview rows.
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
