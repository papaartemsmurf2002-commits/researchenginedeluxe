# WPR104-04 Durable Brute-Force Run Hardening

Owner: Codex Research Agent
Stage: R104 candidate validation on durable evidence
Status: closed
Created: 2026-05-17

## Goal

Make the R104 durable research path truthful and useful for the branch's
primary objective: running long, brute-force-scale candidate discovery on
durable BTC/ETH evidence. The operator UI should no longer make short smoke or
sparse harvest runs look like completion, and run artifacts should expose the
actual search-space coverage and blocker reasons that explain why no candidate
emerged.

## Allowed paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/work_packets/**`
- `docs/stage_reports/**`
- `configs/discovery/**`
- `configs/research/**`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/research_discovery/**`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/contracts/**`
- `tests/research_discovery/**`
- `tests/tradingbotsuite/test_operator_ui.py`

## Constraints

- Keep all research outputs `research_only`, `observe_only`, and
  `promotion_ready: false`.
- Do not add live execution, order placement, runtime-mode changes, live config
  writes, promotion behavior, or sizing behavior.
- The UI remains a thin operator layer over existing research commands,
  readiness checks, jobs, and artifacts.
- Do not fabricate candidate evidence; no candidate pack should be written
  unless existing gates pass.
- Keep output directories constrained to the configured research output root.

## Planned implementation

1. Add discovery search-space summary metadata so manifests and tests show
   planned trials, total combinations, sampled fraction, and exhaustive status.
2. Add R104 durable BTC/ETH discovery profiles that distinguish short standard
   screens from exact bounded brute-force sweeps.
3. Make operator defaults point at durable R104 specs, not legacy smoke/context
   specs.
4. Make the progress API include bounded R104 filesystem evidence so direct CLI
   runs and UI runs both show up in completion state.
5. Refine the Research UI copy and controls around diagnostic, standard, and
   exact sweep tasks so operators know the next durable action.
6. Add focused tests for config coverage, defaults, artifact progress, and UI
   wiring.

## Validation target

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Exit evidence

- Investigated the failed/no-lead R104 durable runs and found completed
  file-system artifacts even though the operator job table did not contain R104
  jobs.
- Added discovery search-space summary metadata to manifests and snapshots so
  exact versus sparse coverage is explicit.
- Added R104 exact bounded BTC/ETH discovery sweep configs with 570240 planned
  combinations per symbol.
- Added R104 deep BTC/ETH historical-cycle configs with larger candidate and
  refinement budgets.
- Rewired operator defaults, progress milestones, and the Research UI to the
  deep/exact durable path.
- Added bounded R104 disk-artifact progress indexing so direct CLI and isolated
  operator outputs can drive milestone state.
- Registered `ISSUE-R104-001` for the remaining durable-data volume blocker.
- Validation:
  - `python -m compileall -q src\tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - JSON parse check for new R104 configs.
  - Playwright desktop/mobile Research page overflow checks passed.
