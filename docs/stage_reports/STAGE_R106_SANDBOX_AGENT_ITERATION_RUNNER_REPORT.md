# Stage R106 Sandbox Agent Iteration Runner Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-242-sandbox-agent-iteration-runner.md`
Status: closed

## Summary

WPR106-242 adds a one-command Rapid Strategy Iteration Sandbox workflow for
agents. It stitches together the existing sandbox intake, archive manifest,
archive-backed sweep, run analysis, hypothesis falsification,
descriptor-only validation request bundle, and global leaderboard steps into a
single research-only iteration manifest.

## Implementation

- Added `src/tradingbotsuite/research_sandbox/iteration.py`.
- Added `run_sandbox_agent_iteration`.
- The workflow accepts either existing `strategy_catalog.json` and
  `venue_archives.json` inputs or local catalog/archive roots that are
  materialized first.
- Generated default specs are 2024+ only and use existing
  `SandboxRunSpec`/`DataWindow` validation.
- Archive-backed execution uses the existing `run_sandbox_archive_sweep`
  runner; no new backtest engine was added.
- The workflow writes `sandbox_iteration_manifest.json` and
  `sandbox_iteration_steps.parquet`.
- The iteration manifest records source input mode, materialized input paths,
  run artifacts, analysis report, hypothesis falsification report,
  strict-validation request bundle, global leaderboard paths, result counts,
  evidence-request counts, and candidate-pack/strict-validation non-execution
  fields.
- Repeated calls with the same content-based iteration identity return the
  existing manifest instead of colliding with the existing run directory.
- Added `run-rapid-strategy-sandbox-iteration` as a research CLI command with
  research-root `--output-dir` enforcement.
- Registered the command in the research command registry and boundary
  contract.
- Extended the sandbox research contract with iteration runner rules.
- Extended the sandbox artifact catalog to discover iteration manifests.

## Boundary

Iteration manifests and steps carry:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `sandbox_only: true`
- `candidate_evidence: false`
- `candidate_pack_eligible: false`

The iteration workflow does not execute strict validation, write candidate
packs, create paper/live signals, define sizing, place orders, mutate runtime
mode, write live configuration, download provider data, or claim promotion
readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 61 passed

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
# 18 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

This packet does not add UI controls, execute strict validation requests, write
candidate packs, or add new venue downloaders. Follow-up work should focus on
more archive-source adapters and richer strategy spreadsheet templates while
preserving the same research-only boundary.
