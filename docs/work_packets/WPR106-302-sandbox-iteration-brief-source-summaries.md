# WPR106-302 Sandbox Iteration Brief Source Summaries

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Preserve compact source routing and ZIP/TAR container diagnostics from
descriptor-only strict-validation request bundles in one-command sandbox
iteration agent briefs, iteration index rows, action queues, and action-plan
items.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-302-sandbox-iteration-brief-source-summaries.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_BRIEF_SOURCE_SUMMARIES_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not execute strict validation, write candidate packs, create paper/live
  signals, define sizing, place orders, change runtime mode, write live
  configuration, download provider data, mutate source archive files, extract
  archive members to disk, or claim promotion readiness.
- Preserve the 2024+ sandbox date floor, source-integrity checks, archive
  routing, trial identity, ranking math, blocker semantics, and evidence
  request selection.
- Treat source summaries as navigation metadata only; they must not alter
  trial estimates, sweep metrics, rankings, eligibility, or request counts.
- Keep projected metadata bounded and deterministic for compact agent handoff
  artifacts.

## Plan

1. Add a compact validation-request source summary helper for iteration agent
   briefs.
2. Include descriptor routing, source path, and bounded container fields in
   each brief `top_validation_requests` item.
3. Prove those fields naturally flow into iteration index rows, strict
   validation action queue items, and agent action-plan items.
4. Add a focused ZIP-backed one-command iteration/index regression test.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Completion Notes

Implemented and closed on 2026-06-19. One-command sandbox iteration agent
briefs now preserve compact source summaries for top descriptor-only
strict-validation requests, including source venue descriptor ID, routing mode,
source path, bounded ZIP/TAR selected-member diagnostics, source metrics, and
market bounds. Iteration indexes, strict-validation action queue items, and
agent action-plan items naturally carry those enriched top request descriptors
from the brief.

This is navigation-only. Trial IDs, market routing, ranking math, blocker
semantics, eligibility flags, evidence-request selection, source archive files,
and strict-validation behavior are unchanged.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "agent_iteration_brief_preserves_validation_request_source_summary"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 1 focused ZIP-backed iteration/source-summary test passed, 165
sandbox tests passed, package compileall passed, 11 import-boundary tests
passed, and 461 contract tests passed.
