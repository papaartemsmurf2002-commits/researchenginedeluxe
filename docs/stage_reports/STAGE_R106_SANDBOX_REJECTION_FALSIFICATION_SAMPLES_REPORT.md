# Stage R106 Sandbox Rejection Falsification Samples Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-311-sandbox-rejection-falsification-samples.md`

## Summary

WPR106-311 surfaces compact rejection/falsification samples in one-command
sandbox iteration handoff artifacts. Completed iterations already wrote
analysis and hypothesis falsification artifacts, but rejection-review queue
items did not identify which failed hypotheses or representative rejected trials
an agent should inspect first. Iteration manifests, agent briefs,
iteration-index rows, rejection-review queue items, recommended action details,
queue summaries, and agent action-plan rows now carry bounded
rejection/falsification samples and falsification decision counts.

The action queue schema version is now 12.

## Implementation

- Added bounded rejection/falsification samples and truncation metadata to
  completed one-command iteration manifests and agent briefs.
- Preflight-blocked iterations now explicitly carry empty rejection sample
  fields.
- Each sample includes hypothesis/family identity, falsification
  decision/reason, best trial identity/status, venue/symbol, compact best-trial
  metrics, tested exit/filter variants, source IDs, and compact
  rejected/blocked/all reason counts.
- Iteration indexes now project samples into rows, rejection-review queue
  items, recommended rejection-review action details, queue summaries, and
  agent action-plan items.
- Focused regressions prove a completed rejected iteration carries the same
  falsified hypothesis and rejected-trial context through manifest, brief,
  index row, rejection queue, action details, action plan, and Parquet outputs.

## Boundary

This is descriptor navigation metadata only. The packet did not execute strict
validation, write candidate packs, create paper/live signals, define sizing,
place orders, change runtime mode, write live configuration, download provider
data, mutate strategy catalogs, mutate archive manifests or source files, or
claim promotion readiness.

The packet did not alter sandbox scoring, ranking math, falsification
decisions, blocker/rejection semantics, evidence-request selection, trial IDs,
archive routing, compatibility preflight, or 2024+ window policy.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "rejection_falsification_samples"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "rejection_falsification_samples or iteration_index"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 1 focused rejection/falsification sample test passed.
- 5 focused rejection/index tests passed.
- 171 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
