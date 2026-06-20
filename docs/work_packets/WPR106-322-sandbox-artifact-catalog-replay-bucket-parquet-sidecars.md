# WPR106-322 Sandbox Artifact Catalog Replay Bucket Parquet Sidecars

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Write compact Parquet sidecars for replay batch-plan archive bucket queues and
bucket representatives so agents can query venue/window-to-plan routing without
loading nested sandbox artifact catalog JSON.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-322-sandbox-artifact-catalog-replay-bucket-parquet-sidecars.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_REPLAY_BUCKET_PARQUET_SIDECARS_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not execute replay commands, strict validation, write candidate packs,
  create paper/live signals, define sizing, place orders, change runtime mode,
  write live configuration, download provider data, mutate strategy catalogs,
  mutate archive manifests/source files, or claim promotion readiness.
- Derive sidecar rows only from already-indexed sandbox artifact catalog rows
  and the bounded replay bucket queues.
- Treat sidecar rows as read-only navigation metadata for agent triage.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness, and
  2024+ window policy.

## Plan

1. Add deterministic Parquet file names and payload paths for replay bucket
   queue and representative sidecars.
2. Flatten archive bucket and archive-window bucket queue items into compact
   row dictionaries with sandbox boundary metadata.
3. Write empty-schema Parquet files when no bucket rows exist.
4. Add focused regressions for non-empty duplicate-ready plans and blocked-only
   empty sidecars.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-321 made bucket representative queues
  available in JSON but left fast Parquet querying unavailable for agents.
- 2026-06-19: Added deterministic Parquet sidecar names and catalog payload
  paths for replay bucket queue rows and bucket representative rows.
- 2026-06-19: Flattened archive bucket and archive-window queue items into
  sandbox-boundary Parquet rows with bucket keys, counts, representative paths,
  and explicit non-executing authorization flags.
- 2026-06-19: Added empty-schema Parquet writes for blocked-only or no-bucket
  catalogs so agent automation can depend on stable file presence and columns.
- 2026-06-19: Added focused regressions for non-empty duplicate-ready sidecars
  and blocked-only empty sidecars.
- 2026-06-19: Updated the sandbox research contract, active index, stage ledger,
  and stage report.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "input_replay"`:
  3 passed, 171 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "input_replay or iteration_index"`:
  7 passed, 167 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`:
  174 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`:
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q`:
  11 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`:
  461 passed.

## Closeout

WPR106-322 is closed. Sandbox artifact catalogs now write compact replay
bucket queue and bucket representative Parquet sidecars beside the existing
catalog JSON and artifact-row Parquet. The sidecars are derived only from
bounded catalog queues, retain sandbox boundary flags, and provide flat
venue/window-to-plan navigation rows for agent automation. No replay command
execution, validation execution, provider download, strict-cycle execution,
candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, strategy catalog mutation, archive manifest/source
mutation, or promotion claim exists.
