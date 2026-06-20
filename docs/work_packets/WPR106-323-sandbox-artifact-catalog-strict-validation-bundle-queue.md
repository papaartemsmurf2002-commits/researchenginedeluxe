# WPR106-323 Sandbox Artifact Catalog Strict Validation Bundle Queue

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Project descriptor-only strict-validation request bundle counts into sandbox
artifact catalog rows, add a top-level strict-validation bundle summary, and
emit a bounded queue so agents can find ready strict-validation handoff
artifacts without opening every bundle JSON.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-323-sandbox-artifact-catalog-strict-validation-bundle-queue.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_STRICT_VALIDATION_BUNDLE_QUEUE_REPORT.md`
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
- Derive strict-validation bundle counts and queue items only from already
  loaded catalog rows and bundle payload metadata.
- Treat bundle queue items as read-only navigation metadata for agent triage.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness, and
  2024+ window policy.

## Plan

1. Project strict-validation request bundle request/deduped/duplicate counts
   into artifact catalog rows.
2. Add a top-level strict-validation bundle summary across run and suite bundle
   artifacts.
3. Add a bounded strict-validation bundle queue with descriptor-only path/count
   metadata for agents.
4. Add focused regressions for run and suite validation bundles.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after finding artifact catalog rows did not expose
  strict-validation bundle `request_count` as queryable agent metadata.
- 2026-06-19: Projected strict-validation bundle IDs, source scope, execution
  mode, request counts, deduped descriptor counts, and duplicate removals into
  sandbox artifact catalog rows.
- 2026-06-19: Added a top-level strict-validation bundle summary and bounded
  descriptor-only bundle queue derived only from catalog rows.
- 2026-06-19: Added focused catalog regressions covering run and suite
  strict-validation bundles, queue counts, summary counts, and non-executing
  authorization flags.
- 2026-06-19: Updated the sandbox research contract, active index, stage ledger,
  and stage report.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "artifact_catalog_indexes_known_artifacts"`:
  1 passed, 173 deselected.
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

WPR106-323 is closed. Sandbox artifact catalogs now expose descriptor-only
strict-validation request bundle counts, a top-level bundle summary, and a
bounded bundle queue for agent triage without opening every bundle JSON. The
queue is read-only navigation metadata and does not authorize or execute strict
validation. No replay command execution, validation execution, provider
download, strict-cycle execution, candidate pack, paper/live artifact,
order/sizing/runtime change, live configuration write, strategy catalog
mutation, archive manifest/source mutation, or promotion claim exists.
