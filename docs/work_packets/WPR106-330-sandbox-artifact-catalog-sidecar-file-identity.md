# WPR106-330 Sandbox Artifact Catalog Sidecar File Identity

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Add file existence, byte-size, and SHA-256 identity metadata to sandbox artifact
catalog sidecar index rows so agents can verify generated catalog, replay, and
strict-validation Parquet sidecars without reopening the full catalog JSON or
recomputing sidecar inventories.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-330-sandbox-artifact-catalog-sidecar-file-identity.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_SIDECAR_FILE_IDENTITY_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not execute sandbox sweeps, strict validation, replay commands, provider
  downloads, candidate-pack writes, paper/live signal generation, sizing, order
  placement, runtime-mode changes, live configuration writes, strategy-catalog
  mutations, archive manifest/source mutations, or promotion claims.
- Hash only catalog writer sidecar outputs produced by the same catalog write.
- File identity rows may expose sidecar path, existence, byte size, SHA-256,
  row count, empty status, and non-authorizing flags.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness,
  strict-validation descriptor queues, sidecar row counts, and the 2024+ window
  policy.

## Plan

1. Add sidecar index columns for existence, byte size, and SHA-256.
2. Compute file identity after companion Parquet sidecars are written and before
   writing the sidecar index and catalog JSON.
3. Keep `write_report=False` behavior non-writing and non-authorizing.
4. Add focused regressions for populated and empty sidecar file identity.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-329 added sidecar index rows with paths
  and row counts but no file identity metadata.
- 2026-06-19: Added sidecar index columns for file existence, byte-size, and
  SHA-256, computed after catalog-written companion Parquet sidecars are
  emitted and before the sidecar index/JSON catalog are written.
- 2026-06-19: Extended populated and integrity-blocked artifact catalog
  regressions to verify sidecar index identity metadata against actual file
  size and SHA-256 values.

## Validation

- 2026-06-19:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "artifact_catalog"`
  passed with 2 passed and 172 deselected.
- 2026-06-19:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`
  passed with 174 passed.
- 2026-06-19:
  `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`
  passed.
- 2026-06-19:
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q`
  passed with 11 passed.
- 2026-06-19:
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  passed with 461 passed.

## Closeout

Closed 2026-06-19. WPR106-330 keeps the artifact catalog sidecar index
research-only and non-authorizing while adding post-write file identity for the
catalog, replay batch-plan, and strict-validation companion Parquet sidecars.
No candidate pack, paper/live signal, order/sizing/runtime change, provider
download, replay execution, validation execution, strategy catalog mutation,
archive manifest/source mutation, live configuration write, or promotion claim
was added.
