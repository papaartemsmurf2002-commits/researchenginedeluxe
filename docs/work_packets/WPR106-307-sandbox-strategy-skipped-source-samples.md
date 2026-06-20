# WPR106-307 Sandbox Strategy Skipped Source Samples

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Expose bounded skipped strategy-catalog source samples in one-command iteration
summaries and iteration-index repair queues so agents can identify the bad
catalog files directly from handoff artifacts.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-307-sandbox-strategy-skipped-source-samples.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_STRATEGY_SKIPPED_SOURCE_SAMPLES_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration.py`
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
- Treat skipped-source samples as descriptor navigation metadata only.
- Derive samples only from already-produced materialized strategy catalog build
  report metadata.
- Keep samples bounded and deterministic.
- Do not alter materialized strategy rows, sweep execution, preflight trial
  estimates, ranking math, blocker semantics, evidence-request selection,
  archive routing, or trial IDs.

## Plan

1. Extend materialized strategy-source summaries with bounded skipped source
   samples carrying source path, suffix, and skip reasons.
2. Project those samples into iteration-index rows, queue items, and
   agent-action-plan items.
3. Add focused regressions proving samples appear in iteration manifests,
   briefs, index rows, repair queues, and action-plan Parquet-visible payloads.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after confirming strategy-source repair queues
  expose skip reason counts but not the skipped source paths needed for direct
  agent repair.
- 2026-06-19: Added bounded `skipped_source_samples` and truncation metadata to
  materialized strategy-source summaries.
- 2026-06-19: Projected skipped-source samples into iteration-index rows,
  strategy-source repair queue items, recommended action details, and global
  agent action-plan items.
- 2026-06-19: Bumped the iteration action queue schema to version 8 because
  queue item payload shape now includes skipped-source samples.
- 2026-06-19: Added focused regressions for real materializer skipped files and
  low-level queue/action-plan propagation.

## Completion Notes

Implemented and closed on 2026-06-19. One-command sandbox iteration
strategy-source summaries now include bounded skipped source samples with
source path, suffix, and skip reasons. Iteration-index rows, strategy-source
repair queue items, recommended action details, and agent action-plan items
carry the same samples so agents can identify bad catalog files directly from
handoff artifacts.

The action queue schema version is now 8.

This is descriptor navigation metadata only. The packet did not alter
materialized strategy rows, sweep execution, preflight trial estimates, trial
metrics, rankings, blocker semantics, evidence-request selection, archive
routing, strict validation behavior, candidate-pack behavior, live/paper signal
state, sizing, order placement, runtime mode, live configuration, provider
access, source catalog files, or promotion state.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "skipped_strategy_source_samples or action_queue_rollups"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 2 focused skipped-source/queue tests passed, 170 sandbox tests
passed, package compileall passed, 11 import-boundary tests passed, and 461
contract tests passed.
