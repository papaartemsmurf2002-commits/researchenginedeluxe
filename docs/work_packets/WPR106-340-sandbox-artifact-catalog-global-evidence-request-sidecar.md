# WPR106-340 Sandbox Artifact Catalog Global Evidence-Request Sidecar

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Flatten bounded global leaderboard `top_hypotheses[*].evidence_request_trial_ids`
into a compact artifact-catalog Parquet sidecar so agents can route
descriptor-only strict-validation requests from global leaderboard output
without opening every leaderboard JSON, companion leaderboard Parquet, or
parsing list-valued top-hypothesis cells first.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-340-sandbox-artifact-catalog-global-evidence-request-sidecar.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_SIDECAR_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, descriptor-only,
  and promotion-ready false.
- Derive sidecar rows only from bounded `top_hypotheses` already present in
  loaded `sandbox_global_leaderboard.json` payloads.
- Do not open or recompute `sandbox_global_leaderboard.parquet` while building
  catalog sidecar rows.
- Do not execute sandbox sweeps, iteration replay commands, strict validation,
  provider downloads, candidate-pack writes, paper/live signal generation,
  sizing, order placement, runtime-mode changes, live configuration writes,
  strategy-catalog mutations, archive manifest/source mutations, or promotion
  claims.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness, and
  the 2024+ window policy.

## Plan

1. Add a global evidence-request sidecar schema and row projector.
2. Register the sidecar in the catalog sidecar index and catalog manifest.
3. Extend focused catalog/global leaderboard regression coverage.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-339 made global top-hypothesis rows
  catalog-queryable while evidence-request trial IDs still lived inside
  list-valued Parquet/JSON cells.
- 2026-06-19: Added a catalog-owned
  `sandbox_artifact_catalog_global_evidence_requests.parquet` schema and row
  projector derived only from loaded global leaderboard JSON
  `top_hypotheses[*].evidence_request_trial_ids`.
- 2026-06-19: Registered the sidecar in the artifact catalog sidecar index with
  post-write file identity metadata and exposed catalog payload path/row-count
  fields.
- 2026-06-19: Extended focused artifact catalog/global leaderboard coverage for
  populated request rows, empty-schema behavior, deterministic row ranks,
  request/source trial IDs, requested-validation labels, source paths, and
  non-authorizing flags.
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

## Closeout

- Closed 2026-06-19. The packet keeps catalog rows research-only,
  observe-only, sandbox-only, descriptor-only, and promotion-ready false. It
  does not open or recompute `sandbox_global_leaderboard.parquet`, execute
  sandbox sweeps, iteration replay commands, strict validation, provider
  downloads, candidate-pack writes, paper/live signal generation, sizing, order
  placement, runtime-mode changes, live configuration writes,
  strategy-catalog mutations, archive manifest/source mutations, or promotion
  claims.
