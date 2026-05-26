# WPR105-104 Required Discovery Wiring Snapshot And Utilization

Owner: Codex Research Agent
Stage: R105 candidate factory component falsification
Status: closed
Created: 2026-05-20

## Goal

Fix operator confusion and correctness around the required discovery workflow:
old/simple artifacts must not make the new required path look complete, exact
discovery buttons must visibly queue the intended long compute job, pause/resume
must continue from durable discovery state, and data-depth readiness must warn
or block when fixture coverage is too small for strict gates.

## Allowed paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/work_packets/**`
- `docs/stage_reports/**`
- `configs/discovery/**`
- `configs/research/**`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/research.html`
- `src/tradingbotsuite/research_discovery/**`
- `tests/tradingbotsuite/test_operator_ui.py`
- `tests/research_discovery/**`
- `tests/contracts/**`

## Constraints

- Preserve research-only and observe-only boundaries.
- Do not add live execution, order placement, runtime-mode mutation, live
  configuration writes, promotion behavior, candidate-pack writing, or sizing
  behavior.
- Do not weaken evidence gates to make weak runs pass.
- Performance claims require manifest evidence and validation.

## Planned validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Changes completed

- Split durable readiness into fixture-integrity readiness and candidate-depth
  readiness. Current BTC/ETH packs remain integrity-ready screening fixtures,
  but they are blocked for candidate-ready one-year evidence because they only
  contain 32 primary 15m bars and 480 one-minute context rows.
- Hardened required-progress predicates so stale/minimal/simple artifacts do
  not mark the checklist complete. Exact discovery must be the current
  exhaustive 570240-trial run and still cannot count while candidate-depth data
  is blocked.
- Made exact discovery operator jobs use a stable run-id output directory by
  default, with auto-resume when an incomplete run_state exists.
- Added active discovery progress fields for the operator console: completed
  trials, total trials, percent, rate, ETA, output directory, run_state path,
  and latest snapshot path.
- Added process-pool execution support to discovery specs and configured the
  BTC/ETH exact sweeps for `executor: process` so long exact sweeps can use
  multiple CPU cores instead of the prior thread-only path.
- Updated the Research UI to keep job feedback beside required buttons, show
  the discovery progress bar/ETA, label current compact data as screening-only,
  and select only the exact required cycle/discovery IDs for required charts.

## Validation run

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_spec.py tests\research_discovery\test_discovery_runner.py::test_discovery_runner_process_executor_smoke tests\tradingbotsuite\test_operator_ui.py::test_operator_research_progress_api_reports_r104_milestones tests\tradingbotsuite\test_operator_ui.py::test_operator_research_progress_api_indexes_bounded_r104_disk_artifacts tests\tradingbotsuite\test_operator_ui.py::test_operator_r104_readiness_api_reports_durable_btc_eth tests\tradingbotsuite\test_operator_ui.py::test_operator_research_job_routes_default_to_r104_deep_and_exact_specs tests\tradingbotsuite\test_operator_ui.py::test_operator_discovery_job_writes_research_only_artifacts tests\tradingbotsuite\test_operator_ui.py::test_operator_discovery_job_can_pause_and_resume -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts tests\research_discovery tests\tradingbotsuite\test_operator_ui.py -q
$env:PYTHONPATH='src'; python -m pytest -q
git diff --check
```

Result: compile passed; focused tests passed; scoped contracts/research/operator
suite passed with `654 passed`; full pytest passed with `1389 passed, 1
skipped`; `git diff --check` passed. Browser smoke covered desktop and 390px
mobile Research UI, no console errors, no mobile horizontal overflow, and the
server was stopped after verification.
