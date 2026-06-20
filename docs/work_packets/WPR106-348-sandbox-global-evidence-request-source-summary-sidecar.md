# WPR106-348 Sandbox Global Evidence-Request Source Summary Sidecar

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Write a compact Parquet sidecar for sandbox artifact catalog global
evidence-request source-context summary count maps so agents can query source
venue, symbol, data family, interval, routing mode, venue descriptor, and
data-path availability without opening the catalog JSON or the full flat
request sidecar.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-348-sandbox-global-evidence-request-source-summary-sidecar.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_EVIDENCE_REQUEST_SOURCE_SUMMARY_SIDECAR_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, descriptor-only,
  and promotion-ready false.
- Derive sidecar rows only from the in-memory global evidence-request summary
  already produced during the same catalog write.
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

1. Add a source-summary Parquet schema and sidecar filename.
2. Flatten source summary count maps into descriptor-only rows with stable
   source field names, values, counts, and summary totals.
3. Register the sidecar in the catalog sidecar index and payload with
   empty-schema behavior.
4. Extend focused artifact catalog regression coverage.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline and diff hygiene.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-347 exposed source-context count maps
  only in the catalog JSON payload and nested summary object.
- 2026-06-19: Added
  `sandbox_artifact_catalog_global_evidence_request_source_summary.parquet`
  with one compact descriptor-only row per non-empty source-context summary
  field/value count.
- 2026-06-19: Registered the sidecar in the catalog sidecar index with
  post-write file identity and exposed its path and row count in the catalog
  payload.
- 2026-06-19: Extended focused artifact catalog regression coverage and updated
  the sandbox contract, active index, stage ledger, and stage report.

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
  leaderboard Parquet files, execute sandbox sweeps, iteration replay commands,
  strict validation, provider downloads, candidate-pack writes, paper/live
  signal generation, sizing, order placement, runtime-mode changes, live
  configuration writes, strategy-catalog mutations, archive manifest/source
  mutations, or promotion claims.
