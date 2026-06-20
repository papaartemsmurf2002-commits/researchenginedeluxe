# WPR106-325 Sandbox Strict Validation Descriptor Catalog Sidecar

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Write a cross-bundle strict-validation descriptor Parquet sidecar from sandbox
artifact catalogs so agents can query individual descriptor-only validation
requests across run and suite bundles without opening each bundle JSON or
bundle Parquet.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-325-sandbox-strict-validation-descriptor-catalog-sidecar.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_STRICT_VALIDATION_DESCRIPTOR_CATALOG_SIDECAR_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not execute strict validation, replay commands, write candidate packs,
  create paper/live signals, define sizing, place orders, change runtime mode,
  write live configuration, download provider data, mutate strategy catalogs,
  mutate archive manifests/source files, or claim promotion readiness.
- Derive descriptor rows only from already-loaded strict-validation bundle JSON
  payloads that pass sandbox boundary validation.
- Flatten only read-only descriptor identity, source, venue, market-window,
  metric, and non-authorizing handoff metadata.
- Empty catalogs must still write a stable empty-schema Parquet sidecar for
  automation.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness, and
  2024+ window policy.

## Plan

1. Add a strict-validation descriptor catalog sidecar name, schema, and row
   flattener.
2. Emit descriptor sidecar path, row count, and compact summary metadata from
   artifact catalog payloads.
3. Add focused regressions for run/suite descriptor sidecar rows and empty
   sidecar behavior.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after finding catalog-level strict-validation
  bundle queues are queryable, but individual descriptor requests still require
  opening each bundle JSON or bundle Parquet.
- 2026-06-19: Added a cross-bundle strict-validation descriptor catalog sidecar
  with stable empty-schema behavior and row-count / summary metadata in
  artifact catalog payloads.
- 2026-06-19: Added focused catalog regressions for populated run/suite
  descriptor rows, multi-venue descriptor coverage, and empty no-bundle
  descriptor sidecars.
- 2026-06-19: Updated the sandbox research contract, active index, stage ledger,
  and stage report.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "artifact_catalog"`:
  2 passed, 172 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`:
  174 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`:
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q`:
  11 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`:
  461 passed.

## Closeout

WPR106-325 is closed. Sandbox artifact catalogs now write
`sandbox_artifact_catalog_strict_validation_descriptors.parquet` beside catalog
outputs. The sidecar is derived only from already-loaded strict-validation
bundle JSON payloads, keeps sandbox boundary flags, exposes descriptor identity,
source trial, venue, symbol, market-window, source routing, compact source
metrics, and explicit non-authorizing flags, and writes an empty-schema Parquet
file when no descriptor rows exist. No replay command execution, validation
execution, provider download, strict-cycle execution, candidate pack,
paper/live artifact, order/sizing/runtime change, live configuration write,
strategy catalog mutation, archive manifest/source mutation, or promotion claim
exists.
