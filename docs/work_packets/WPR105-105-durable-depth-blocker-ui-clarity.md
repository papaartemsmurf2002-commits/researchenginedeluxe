# WPR105-105 Durable Depth Blocker UI Clarity

Owner: Codex Research Agent
Stage: R105 candidate factory component falsification
Status: closed
Created: 2026-05-20

## Goal

Make the Research UI explicit that `Durable data depth` being blocked is
intentional and cannot be unblocked by a compute run. The operator should see
that the unblock action is adding or selecting expanded durable BTC/ETH data,
then rerunning readiness.

## Allowed paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/**`
- `docs/stage_reports/**`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_operator_ui.py`

## Constraints

- Preserve research-only and observe-only boundaries.
- Do not add live execution, order placement, runtime-mode mutation, live
  configuration writes, promotion behavior, candidate-pack writing, or sizing
  behavior.
- Do not weaken evidence gates or make compact fixtures pass candidate-depth
  readiness.

## Planned validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
git diff --check
```

## Changes completed

- The required input step now explicitly says a data-depth block cannot be
  unblocked by a compute run.
- Blocked `Durable data depth` now shows an enabled `Show Data Gap` action
  instead of a disabled `Run` button.
- Other blocked/waiting milestone buttons now render as `Data Required` or
  `Waiting` instead of looking like inert run buttons.
- The readiness feedback tells the operator to add expanded BTC/ETH durable
  historical fixture packs and updated readiness hashes, then rerun the
  readiness check.

## Validation run

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_research_page_keeps_hmm_knn_monitoring_observe_only tests\tradingbotsuite\test_operator_ui.py::test_operator_research_progress_api_reports_r104_milestones -q
```

Result: 2 focused tests passed.
