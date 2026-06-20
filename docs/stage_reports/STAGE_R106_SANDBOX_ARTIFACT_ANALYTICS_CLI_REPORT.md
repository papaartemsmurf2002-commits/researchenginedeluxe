# Stage R106 Sandbox Artifact Analytics CLI Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-233-sandbox-artifact-analytics-cli.md`
Status: closed

## Summary

WPR106-233 adds a fast read-only analytics surface for Rapid Strategy
Iteration Sandbox runs. Agents can now summarize compact sandbox Parquet/JSON
artifacts without manually opening full result tables and without turning
sandbox rows into candidate evidence.

## Implementation

- Added `src/tradingbotsuite/research_sandbox/analytics.py`.
- Added `summarize_sandbox_run`, which reads a sandbox run manifest,
  rankings Parquet, and evidence-request JSON.
- The analysis validates sandbox boundary flags on the manifest,
  evidence-request descriptors, and rankings Parquet before summarizing.
- The summary includes status counts, venue counts, family counts,
  exit/filter summaries, rejection reason counts, market-source summaries,
  top-ranked rows, and evidence-request trial IDs.
- Added `analysis_summary.json` writing inside the sandbox run directory.
- Added `summarize-rapid-strategy-sandbox` as a research CLI command with
  research-root `--run-dir` enforcement.
- Registered the command in the research command registry and boundary
  contract.

## Boundary

The analysis report is still a sandbox artifact. It carries:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `sandbox_only: true`
- `candidate_evidence: false`
- `candidate_pack_eligible: false`

It does not write candidate packs, create paper/live signals, change sizing,
place orders, mutate runtime mode, write live configuration, or claim promotion
readiness.

## Validation

Final validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
# 33 passed

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
# 9 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

This packet does not add a UI page, rich SQL/DuckDB-style interactive querying,
or automatic strict-cycle execution from evidence requests. Those remain
separate follow-up work under the active sandbox objective.
