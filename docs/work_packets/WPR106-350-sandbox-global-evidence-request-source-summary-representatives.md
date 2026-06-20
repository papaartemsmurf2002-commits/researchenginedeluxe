# WPR106-350 Sandbox Global Evidence-Request Source Summary Representatives

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Enrich the sandbox artifact catalog global evidence-request source-summary
Parquet sidecar with bounded representative evidence-request/source IDs and
source artifact paths per source-context field/value row. Agents should be able
to jump from a compact source coverage row to concrete descriptor-only
strict-validation request rows without opening bucket representative sidecars
or scanning the full flat request table first.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-350-sandbox-global-evidence-request-source-summary-representatives.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_EVIDENCE_REQUEST_SOURCE_SUMMARY_REPRESENTATIVES_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, descriptor-only
  where applicable, and promotion-ready false.
- Derive representative fields only from the in-memory global evidence-request
  rows already produced during the same catalog write.
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

1. Add bounded representative JSON-list columns to the source-summary sidecar
   schema.
2. Populate those columns from the already-flattened in-memory global
   evidence-request rows while preserving deterministic order.
3. Extend focused artifact catalog regression coverage.
4. Update the sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline and diff hygiene.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-349 added unique counts and market
  windows to the source-summary sidecar, but the sidecar still required a
  second sidecar lookup to jump from source coverage rows to concrete
  descriptor-only evidence requests.
- 2026-06-19: Added bounded representative columns to the source-summary
  sidecar for evidence-request trial IDs, source trial IDs, source request IDs,
  source artifact paths, and source leaderboard JSON paths.
- 2026-06-19: Populated representative columns from already-flattened
  in-memory global evidence-request rows using deterministic leaderboard rank,
  score, request row rank, source path, and trial ID ordering.
- 2026-06-19: Extended artifact catalog regression coverage to assert the
  summary sidecar's representative JSON-list cells match the concrete flat
  global evidence-request rows they summarize.
- 2026-06-19: Updated the sandbox contract, active index, stage ledger, and
  stage report.

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
