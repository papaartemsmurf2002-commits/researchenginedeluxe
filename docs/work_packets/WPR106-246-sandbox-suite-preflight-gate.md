# WPR106-246 Sandbox Suite Preflight Gate

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Make Rapid Strategy Iteration Sandbox suites agent-ready by running
compatibility preflight for each suite case before archive sweep execution.
Batch runs should still produce complete suite indexes when some cases are
fully blocked, but must avoid sweep, analysis, and evidence-request work for
cases that have zero runnable trials.

## Scope

- Integrate `preflight_sandbox_compatibility()` into `run_sandbox_suite()` for
  every case after loading spec, strategy catalog, and venue archives.
- Write preflight artifacts under each suite case directory before the run
  directory.
- Add case-index fields for preflight artifact paths, status counts,
  runnable/blocked trial estimates, and blocker reason counts.
- If a case has zero runnable trials, add a blocked case-index row, do not run
  `run_sandbox_archive_sweep()`, do not summarize a run, and do not emit suite
  evidence requests for that case.
- Preserve current suite behavior for runnable cases.
- Update suite manifest aggregate counts to include runnable/blocked preflight
  estimates and skipped case counts.
- Add focused sandbox tests for mixed runnable/blocked suites and CLI payload
  count fields.
- Update sandbox contract and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-246-sandbox-suite-preflight-gate.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_SUITE_PREFLIGHT_GATE_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/falsification.py`
- `src/tradingbotsuite/research_sandbox/suite.py`
- `src/tradingbotsuite/main.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Suite runs write compatibility preflight artifacts per case before any case
  sweep.
- Suite indexes expose preflight paths, runnable/blocked trial estimates, and
  blocker reason counts.
- Runnable cases still produce run manifests, analysis reports, rankings, and
  suite evidence-request descriptors.
- Zero-runnable cases are represented as blocked in suite indexes and
  manifests without writing run manifests or evidence-request descriptors.
- CLI suite payloads expose runnable/blocked/skipped case counts.
- Generated artifacts keep `research_only`, `observe_only`,
  `promotion_ready: false`, `sandbox_only`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- Validation includes focused sandbox tests, import-boundary tests, package
  compile, and the contract baseline when the local validation environment
  allows pytest-asyncio socket setup.

## Boundary

This packet changes suite orchestration only. It does not alter sandbox scoring
math, execute strict validation, write candidate packs, create paper/live
signals, define sizing, place orders, mutate runtime mode, write live
configuration, download provider data, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. Suite runs now execute compatibility
preflight for each case after loading the case spec, strategy catalog, and
venue archive manifest. Preflight artifacts are written under
`preflights/<case_id>/...` inside the suite directory before any case sweep is
attempted.

Runnable cases preserve the existing workflow: archive sweep, run analysis,
suite index row, and suite evidence-request aggregation. Cases with zero
runnable trials now write a `blocked_by_preflight` case-index row with
preflight paths/counts and no run manifest, no analysis report, and no
evidence-request descriptors. Suite hypothesis summarization skips those
intentional blocked rows while still failing if a non-blocked row is missing a
run directory.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 69 sandbox tests passed, 11 import-boundary tests passed,
package compileall passed, and the full contract baseline passed with 461
tests.
