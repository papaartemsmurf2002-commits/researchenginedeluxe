# WPR106-352 Sandbox Global Evidence-Request Source Priority Queue

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Add a bounded source-priority queue Parquet sidecar to the sandbox artifact
catalog, derived from the global evidence-request source-summary rows. Agents
should be able to inspect the highest-priority source venue, symbol, data
family, interval, routing mode, venue descriptor, and data-path coverage rows
across all source-context fields without opening the full flat global
evidence-request table first.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-352-sandbox-global-evidence-request-source-priority-queue.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_EVIDENCE_REQUEST_SOURCE_PRIORITY_QUEUE_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, descriptor-only
  where applicable, and promotion-ready false.
- Derive source-priority queue rows only from in-memory global evidence-request
  source-summary rows produced during the same catalog write.
- Do not open per-run evidence request files, open or recompute global
  leaderboard Parquet files, execute sandbox sweeps, iteration replay commands,
  strict validation, provider downloads, candidate-pack writes, paper/live
  signal generation, sizing, order placement, runtime-mode changes, live
  configuration writes, strategy-catalog mutations, archive manifest/source
  mutations, or promotion claims.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness, and
  the 2024+ window policy.

## Plan

1. Add a source-priority queue sidecar name, limit, schema, and row builder.
2. Sort source-summary rows by best leaderboard/source metric context and
   compact counts while preserving deterministic ties.
3. Register and write the sidecar from the artifact catalog writer.
4. Extend focused artifact catalog regression coverage for empty and non-empty
   catalogs.
5. Update the sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline and diff hygiene.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-351 added best-context fields to
  source-summary rows, but agents still needed to scan the full source-summary
  sidecar or apply their own cross-field sorting to find the highest-priority
  source coverage rows.
- 2026-06-19: Added
  `sandbox_artifact_catalog_global_evidence_request_source_priority_queue.parquet`
  with bounded rows derived only from in-memory source-summary rows.
- 2026-06-19: Sorted source-priority rows by best leaderboard rank, best global
  score, best source metric rank/score, unique request-trial count,
  source-context count, and deterministic source field/value ties.
- 2026-06-19: Registered the sidecar in the artifact catalog sidecar index with
  post-write file identity and exposed queue path/count/limit fields in the
  catalog payload.
- 2026-06-19: Extended artifact catalog regression coverage for empty,
  failed-integrity, and non-empty global evidence-request catalog paths.

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

## Closeout

- Closed 2026-06-19. The packet keeps all outputs research-only, observe-only,
  sandbox-only, descriptor-only where applicable, and promotion-ready false. It
  does not open per-run evidence request files, open or recompute global
  leaderboard Parquet files, execute sandbox sweeps, iteration replay
  commands, strict validation, provider downloads, candidate-pack writes,
  paper/live signal generation, sizing, order placement, runtime-mode changes,
  live configuration writes, strategy-catalog mutations, archive
  manifest/source mutations, or promotion claims.
