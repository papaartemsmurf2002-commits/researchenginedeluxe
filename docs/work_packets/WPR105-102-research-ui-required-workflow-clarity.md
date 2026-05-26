# WPR105-102 Research UI Required Workflow Clarity

Owner: Codex Research Agent
Stage: R105 candidate factory component falsification
Status: closed
Created: 2026-05-19

## Goal

Reduce Research tab crowding and make the required evidence workflow explicit.
The checklist at the top should be the single required run path; diagnostics,
compatibility runs, hardware probes, HMM/KNN experiments, and legacy surfaces
must be clearly secondary.

## Allowed paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/**`
- `docs/stage_reports/**`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_operator_ui.py`

## Constraints

- UI-only workflow clarity pass.
- Preserve research-only and observe-only boundaries.
- Do not add live execution, order placement, runtime-mode mutation, live
  configuration writes, promotion behavior, candidate-pack writing, or sizing
  behavior.
- Do not change research-cycle, discovery, backtest, feature, gate, or scoring
  semantics.

## Planned validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_research_page_keeps_hmm_knn_monitoring_observe_only -q
git diff --check
```

## Completed changes

- Reworked the Research tab around a top-level Required Evidence Checklist
  and explicit “Only this checklist is required” operator instruction.
- Split manual required presets from optional diagnostics and legacy
  compatibility controls.
- Moved provider pipeline diagnostics, HMM/KNN research experiments, and
  hardware utilization benchmark controls behind an optional diagnostics
  disclosure.
- Removed stale operator-facing R104 headings from the required workflow and
  sanitized dynamic defaults so the internal spec label does not become the
  visible workflow name.
- Tightened mobile wrapping for long artifact paths, status values, tables,
  and diagnostic controls.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_research_page_keeps_hmm_knn_monitoring_observe_only -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Results:

- Focused operator UI test: `1 passed`.
- Contracts: `427 passed`.
- Browser smoke: desktop and 390px mobile Research page loaded; optional
  diagnostics opened; no console errors on fresh session; no page-level
  horizontal overflow; stale R104 headings absent.
