# WPR106-306 Sandbox Strategy Source Repair Queue

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Surface skipped materialized strategy catalog sources as first-class iteration
index repair work so agents can fix bad catalog files without reopening build
reports.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-306-sandbox-strategy-source-repair-queue.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_STRATEGY_SOURCE_REPAIR_QUEUE_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration_index.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not execute strict validation, write candidate packs, create paper/live
  signals, define sizing, place orders, change runtime mode, write live
  configuration, download provider data, mutate source catalog files, or claim
  promotion readiness.
- Treat strategy-source repair queues as descriptor navigation metadata only.
- Derive queue membership only from already-indexed iteration manifest or agent
  brief metadata.
- Do not alter sweep execution, preflight trial estimates, ranking math,
  blocker semantics, evidence-request selection, archive routing, or materialized
  strategy catalog rows.

## Plan

1. Add a deterministic recommended action for rows with skipped strategy catalog
   sources or source skip reason counts.
2. Add a bounded `strategy_source_repair_queue` to iteration indexes and global
   agent action plans.
3. Preserve queue summaries and Parquet output with the same sandbox boundary
   flags as existing queues.
4. Add focused regressions for skipped-source queue membership, ordering, and
   action-plan source queue attribution.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after confirming skipped strategy catalog sources
  were projected into iteration rows and totals, but not exposed as a dedicated
  repair worklist.
- 2026-06-19: Added `repair_strategy_catalog_sources` recommended actions for
  rows with skipped materialized strategy catalog sources or source skip reason
  counts.
- 2026-06-19: Added a bounded `strategy_source_repair_queue`, queue summaries,
  source queue attribution for agent action-plan items, and action queue schema
  version 7.
- 2026-06-19: Added queue item and action-plan source diagnostics for
  strategy-source status/skip reason counts, preserving descriptor-only
  sandbox boundaries.
- 2026-06-19: Updated focused iteration-index regressions to prove skipped
  strategy sources appear in queue counts, truncated queue rollups, and global
  agent action plans.

## Completion Notes

Implemented and closed on 2026-06-19. Sandbox iteration indexes now expose
skipped materialized strategy catalog sources as a first-class
`strategy_source_repair_queue`. Rows with skipped strategy sources or source
skip reason counts receive the deterministic `repair_strategy_catalog_sources`
recommended action, and the global agent action plan links those items back to
`strategy_source_repair_queue`.

Queue items and summaries now preserve compact strategy-source status, suffix,
and skip-reason counts so agents can identify bad catalog inputs without
reopening materializer build reports. The action queue schema is version 7.

This is descriptor navigation metadata only. The packet did not alter
materialized strategy rows, sweep execution, preflight trial estimates, trial
metrics, rankings, blocker semantics, evidence-request selection, archive
routing, strict validation behavior, candidate-pack behavior, live/paper signal
state, sizing, order placement, runtime mode, live configuration, provider
access, source catalog files, or promotion state.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index_summarizes_agent_iterations_and_briefs or action_queue_rollups or queues_archive_window_repairs"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 3 focused iteration-index queue tests passed, 169 sandbox tests
passed, package compileall passed, 11 import-boundary tests passed, and 461
contract tests passed.
