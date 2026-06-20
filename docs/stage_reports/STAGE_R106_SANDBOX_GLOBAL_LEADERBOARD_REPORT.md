# Stage R106 Sandbox Global Leaderboard Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-240-sandbox-global-leaderboard.md`
Status: closed

## Summary

WPR106-240 adds a global leaderboard for accumulated Rapid Strategy Iteration
Sandbox run artifacts. Agents can now scan a research output root and see which
hypotheses were blocked, falsified, screened positive, or emitted
strict-validation request descriptors across multiple archive-backed runs.

## Implementation

- Added `src/tradingbotsuite/research_sandbox/leaderboard.py`.
- Added `build_sandbox_global_leaderboard`.
- The scanner discovers existing sandbox run `manifest.json` files under a
  research output root.
- Source manifests, rankings Parquet files, and evidence-request JSON files are
  validated for sandbox boundary flags before aggregation.
- Leaderboard rows aggregate by hypothesis and family across runs, venues,
  symbols, data families, holding periods, exit variants, and filter variants.
- Rows include run counts, result counts, screened/rejected/blocked counts,
  best trial metrics, tested dimensions, evidence-request trial IDs, blocker
  and rejection reason counts, and a sandbox-only leaderboard decision.
- Output writes `sandbox_global_leaderboard.json` and
  `sandbox_global_leaderboard.parquet`.
- Added `rank-rapid-strategy-sandbox-artifacts` as a research CLI command with
  research-root `--root-dir` and `--output-dir` enforcement.
- Registered the command in the research command registry and boundary
  contract.
- Extended the sandbox research contract with global leaderboard rules.
- Extended the sandbox artifact catalog to discover global leaderboard reports.

## Boundary

Global leaderboards are sandbox analysis artifacts. They carry:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `sandbox_only: true`
- `candidate_evidence: false`
- `candidate_pack_eligible: false`

They do not execute sandbox runs, execute strict validation, write candidate
packs, create paper/live signals, define sizing, place orders, mutate runtime
mode, write live configuration, or claim promotion readiness.

## Validation

Focused validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
# 55 passed

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
# 16 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed
```

Contract baseline attempt:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 460 passed, 1 pytest-asyncio setup error
```

The baseline failure occurred before the affected async contract test body ran:
Windows failed to create the event-loop `socket.socketpair()` with
`WinError 10055`. `ISSUE-R106-026` tracks this local validation-environment
blocker.

## Remaining Work

This packet does not execute strict validation requests, generate historical
cycle specs, add UI exploration, write candidate packs, or fix the local Windows
socket exhaustion condition. Those remain separate follow-up work under the
active sandbox objective and known-issues process.
