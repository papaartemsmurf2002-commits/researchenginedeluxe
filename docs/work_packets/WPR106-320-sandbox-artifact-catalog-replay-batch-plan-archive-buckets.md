# WPR106-320 Sandbox Artifact Catalog Replay Batch Plan Archive Buckets

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Project descriptor-only replay batch-plan archive and archive-window bucket
counts into sandbox artifact catalog rows, summaries, and queue items so agents
can find OKX/Bybit/Hyperliquid replay coverage without opening each batch-plan
JSON file.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-320-sandbox-artifact-catalog-replay-batch-plan-archive-buckets.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_REPLAY_BATCH_PLAN_ARCHIVE_BUCKETS_REPORT.md`
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
- Treat replay batch-plan archive bucket metadata as read-only navigation
  metadata only.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness, and
  2024+ window policy.

## Plan

1. Project ready/planned archive bucket and archive-window bucket count maps
   from batch-plan summaries into artifact catalog rows.
2. Aggregate those maps into top-level catalog replay batch-plan summaries.
3. Include the maps on bounded replay batch-plan queue items.
4. Add focused regressions for duplicate-rich ready plans and blocked-only
   plans.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after confirming replay batch-plan JSON summaries
  carry ready/planned archive bucket maps, but artifact catalog rows and queues
  do not expose those maps for multi-venue agent triage.
- 2026-06-19: Projected descriptor-only ready/planned archive bucket and
  archive-window bucket count maps into sandbox artifact catalog rows,
  top-level replay batch-plan summaries, and bounded replay batch-plan queue
  items.
- 2026-06-19: Added focused regressions for duplicate-rich ready batch plans and
  blocked-only batch plans so catalog rows, summaries, and queue items preserve
  bucket maps without authorizing replay, validation, candidate packs, or
  promotion.
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

WPR106-320 is closed. Sandbox artifact catalogs now expose descriptor-only input
replay batch-plan archive bucket and archive-window bucket maps at the row,
summary, and bounded queue levels for rapid multi-venue agent triage. The maps
are derived only from already-loaded batch-plan JSON summaries and remain
read-only navigation metadata. No replay command execution, validation
execution, provider download, strict-cycle execution, candidate pack,
paper/live artifact, order/sizing/runtime change, live configuration write,
strategy catalog mutation, archive manifest/source mutation, or promotion claim
exists.
