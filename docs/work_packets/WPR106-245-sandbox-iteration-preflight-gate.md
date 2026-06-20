# WPR106-245 Sandbox Iteration Preflight Gate

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Make the one-command Rapid Strategy Iteration Sandbox workflow agent-ready by
running the compatibility preflight as a first-class iteration step before the
archive sweep. Iterations should expose runnable/blocked trial estimates and
avoid expensive sweep, analysis, falsification, validation-request, and
leaderboard work when the preflight proves there are zero runnable trials.

## Scope

- Integrate `preflight_sandbox_compatibility()` into
  `run_sandbox_agent_iteration()` after strategy/archive/spec resolution and
  before `run_sandbox_archive_sweep()`.
- Write preflight artifacts under the iteration directory.
- Add a `compatibility_preflight` iteration step with artifact paths and
  aggregate counts.
- Add top-level iteration manifest fields for preflight JSON/Parquet paths,
  runnable/blocked estimates, row count, and blocker reason counts.
- If `runnable_trial_estimate == 0`, stop the iteration after preflight and
  write a closed manifest with no sweep, no strict validation request bundle,
  no leaderboard refresh, and explicit skipped downstream steps.
- Preserve existing behavior when runnable trials exist.
- Add focused API/CLI tests for successful preflight integration and zero
  runnable fail-fast behavior.
- Update sandbox contract and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-245-sandbox-iteration-preflight-gate.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_PREFLIGHT_GATE_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- One-command sandbox iterations always include a compatibility preflight step
  before archive sweep execution.
- Iteration manifests expose preflight artifact paths, runnable/blocked trial
  estimates, status counts, and blocker reason counts.
- Runnable iterations still complete archive sweep, analysis, hypothesis
  falsification, descriptor-only validation bundle export, and leaderboard
  refresh.
- Fully blocked iterations write preflight artifacts and a final iteration
  manifest, but do not execute sandbox sweep or downstream analysis/bundle
  steps.
- Generated artifacts keep `research_only`, `observe_only`,
  `promotion_ready: false`, `sandbox_only`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- Validation includes focused sandbox tests, import-boundary tests, package
  compile, and the contract baseline when the local validation environment
  allows pytest-asyncio socket setup.

## Boundary

This packet changes iteration orchestration only. It does not alter sandbox
scoring math, execute strict validation, write candidate packs, create
paper/live signals, define sizing, place orders, mutate runtime mode, write
live configuration, download provider data, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. Agent iterations now run
`preflight_sandbox_compatibility()` after strategy/archive/spec resolution and
before the archive-backed sweep. The iteration manifest records preflight
artifact paths, row counts, status counts, runnable/blocked trial estimates,
and blocker reason counts. The iteration step ledger includes a
`compatibility_preflight` step before `archive_sweep`.

When preflight finds zero runnable trials, the iteration writes a final
`blocked_by_preflight` manifest with the preflight JSON/Parquet artifacts and
explicitly skipped downstream steps for archive sweep, analysis, hypothesis
falsification, validation-request bundle export, and global leaderboard
refresh. It does not execute the sweep or write downstream artifacts in that
case. Runnable iterations preserve the existing sweep, analysis,
falsification, descriptor-only validation bundle, and leaderboard workflow.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 68 sandbox tests passed, 11 import-boundary tests passed,
package compileall passed, and the full contract baseline passed with 461
tests. The first full-contract attempt reached 460 passed tests before the
known local Windows pytest-asyncio `WinError 10055` socket setup failure; an
immediate rerun passed cleanly.
