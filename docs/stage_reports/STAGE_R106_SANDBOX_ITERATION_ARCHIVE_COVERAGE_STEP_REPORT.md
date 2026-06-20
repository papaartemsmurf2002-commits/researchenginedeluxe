# Stage R106 Sandbox Iteration Archive Coverage Step Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-262-sandbox-iteration-archive-coverage-step.md`
Status: closed

## Summary

WPR106-262 makes archive coverage a first-class artifact in the one-command
sandbox agent iteration. Each new iteration now writes an archive coverage
matrix before compatibility preflight and records coverage plus source-audit
paths/counts in the iteration manifest.

## Implementation

- Added archive coverage generation to
  `tradingbotsuite.research_sandbox.iteration.run_sandbox_agent_iteration`
  after archive manifest intake/materialization and before compatibility
  preflight.
- Added an `archive_coverage_matrix` iteration step with coverage JSON/Parquet,
  source-audit JSON/Parquet, descriptor counts, bucket counts, status counts,
  and venue counts.
- Added coverage and source-audit fields to completed and
  `blocked_by_preflight` iteration manifests.
- Included an archive-coverage step version in iteration identity so new runs
  do not accidentally reuse older manifests that lacked coverage evidence.
- Extended cached iteration reuse validation to require coverage/source-audit
  JSON boundary checks and coverage/source-audit Parquet existence before
  returning `reused_existing: true`.
- Added focused sandbox tests for completed iterations, blocked iterations,
  missing cached coverage Parquet artifacts, and promotable cached coverage JSON
  artifacts.
- Updated the sandbox research contract and active index.

## Boundary

The packet only adds read-only archive-readiness evidence to research-only
sandbox iteration manifests. It does not change strategy math, trial identity
semantics beyond the cache-versioned iteration wrapper, sweep execution
semantics, strict validation execution, candidate-pack generation, paper/live
signals, sizing, order placement, runtime mode, live configuration, provider
downloads, source archive mutation, or promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "agent_iteration and (coverage or materializes or skips_downstream or runs_sandbox_agent_iteration_under_research_root)"
# 5 passed, 85 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 90 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

`git diff --check` reported only existing LF-to-CRLF working-copy warnings and
no whitespace errors.

## Remaining Work

The one-command agent iteration now exposes strategy intake, archive manifest
intake, archive coverage, compatibility preflight, sweep execution, analysis,
falsification, validation-request export, and global leaderboard refresh as
searchable iteration steps. Later packets can add UI navigation over the
coverage matrix if operator-side browsing becomes necessary.
