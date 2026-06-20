# WPR106-311 Sandbox Rejection Falsification Samples

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Expose bounded rejection and falsification samples in one-command iteration
manifests, agent briefs, and iteration-index queues so agents can identify
failed hypotheses and representative rejected or blocked trials directly from
handoff artifacts without reopening full ranking or falsification Parquet rows.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-311-sandbox-rejection-falsification-samples.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_REJECTION_FALSIFICATION_SAMPLES_REPORT.md`
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
  configuration, download provider data, mutate strategy catalogs, mutate
  archive manifests/source files, or claim promotion readiness.
- Treat rejection and falsification samples as descriptor navigation metadata
  only.
- Derive samples only from already-produced sandbox analysis and hypothesis
  falsification artifacts for the same one-command iteration.
- Keep samples bounded and deterministic.
- Do not alter sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, preflight
  behavior, archive routing, or 2024+ window policy.

## Plan

1. Add bounded rejection/falsification samples and truncation metadata to
   completed one-command iteration manifests and agent briefs.
2. Keep preflight-blocked iterations explicit with empty rejection sample
   fields.
3. Project the samples into iteration-index rows, rejection-review queue items,
   recommended rejection-review action details, and agent-action-plan items.
4. Add focused regressions proving falsified/rejected hypotheses carry
   decision, reason, trial identity, venue, symbol, metrics, and reason counts
   through the handoff path.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after confirming completed one-command iteration
  handoffs can request rejection/falsification review but do not expose compact
  representative failed hypothesis or rejected-trial samples.
- 2026-06-19: Added bounded rejection/falsification samples and truncation
  metadata to completed iteration manifests and agent briefs, with explicit
  empty sample fields for preflight-blocked iterations.
- 2026-06-19: Projected samples and falsification decision counts into
  iteration-index rows, rejection-review queue items, recommended action
  details, queue summaries, and global agent action-plan items.
- 2026-06-19: Bumped the iteration action queue schema to version 12 because
  queue and action-plan payloads now include rejection/falsification samples.
- 2026-06-19: Added focused regressions for completed rejected iterations and
  rejection-review handoff propagation.

## Completion Notes

Implemented and closed on 2026-06-19. Completed one-command sandbox iteration
manifests and agent briefs now include bounded rejection/falsification samples
derived from existing sandbox analysis and hypothesis falsification artifacts.
Iteration-index rows, rejection-review queue items, recommended rejection
action details, queue summaries, and global agent action-plan items carry the
same navigation context.

The action queue schema version is now 12.

This is descriptor navigation metadata only. The packet did not alter sandbox
scoring, ranking math, falsification decisions, blocker/rejection semantics,
evidence-request selection, trial IDs, archive routing, preflight behavior,
strict validation behavior, candidate-pack behavior, live/paper signal state,
sizing, order placement, runtime mode, live configuration, provider access,
strategy catalogs, archive manifests/source files, or promotion state.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "rejection_falsification_samples"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "rejection_falsification_samples or iteration_index"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 1 focused rejection/falsification sample test passed, 5 focused
rejection/index tests passed, 171 sandbox tests passed, package compileall
passed, 11 import-boundary tests passed, and 461 contract tests passed.
