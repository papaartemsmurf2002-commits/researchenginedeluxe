# WPR106-339 Sandbox Artifact Catalog Global Top-Hypotheses Sidecar

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Flatten bounded `top_hypotheses` rows from indexed
`sandbox_global_leaderboard.json` artifacts into a compact artifact-catalog
Parquet sidecar so agents can query global hypothesis ranking and falsification
state from catalog output without opening every leaderboard JSON or companion
leaderboard Parquet file first.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-339-sandbox-artifact-catalog-global-top-hypotheses-sidecar.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_GLOBAL_TOP_HYPOTHESES_SIDECAR_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Derive sidecar rows only from bounded `top_hypotheses` already present in the
  loaded `sandbox_global_leaderboard.json` payload.
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

1. Add a global top-hypotheses sidecar schema and row projector.
2. Register the sidecar in the catalog sidecar index and catalog manifest.
3. Extend focused catalog/global leaderboard regression coverage.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-338 made global bucket preview rows
  catalog-queryable while global hypothesis preview rows still required opening
  leaderboard JSON or Parquet artifacts.
- 2026-06-19: Added a catalog-owned
  `sandbox_artifact_catalog_global_top_hypotheses.parquet` sidecar schema and
  row projector derived only from loaded global leaderboard JSON
  `top_hypotheses` preview rows.
- 2026-06-19: Registered the sidecar in the catalog sidecar index with
  post-write file identity metadata and exposed catalog payload path/row-count
  fields.
- 2026-06-19: Extended focused artifact catalog/global leaderboard coverage for
  populated and empty-schema sidecar behavior, non-authorizing flags, source
  leaderboard paths, rank preservation, tested dimensions, decision counts, and
  representative metadata.
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
  observe-only, sandbox-only, and promotion-ready false. It does not open or
  recompute `sandbox_global_leaderboard.parquet`, execute sandbox sweeps,
  iteration replay commands, strict validation, provider downloads,
  candidate-pack writes, paper/live signal generation, sizing, order placement,
  runtime-mode changes, live configuration writes, strategy-catalog mutations,
  archive manifest/source mutations, or promotion claims.
