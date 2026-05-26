# WPR105-103 Research Chart Readability And Next Action

Owner: Codex Research Agent
Stage: R105 candidate factory component falsification
Status: closed
Created: 2026-05-20

## Goal

Fix the Research tab graph section shown in the operator screenshot. Charts must
be readable, bounded, and honest about whether they are showing required
evidence or diagnostic/benchmark artifacts. The page should also make the next
operator action clear without relying on tiny chart labels.

## Allowed paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/**`
- `docs/stage_reports/**`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_operator_ui.py`

## Constraints

- UI-only chart and operator guidance pass.
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
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Completed changes

- Renamed the chart section to Required Evidence Profitability Chart and
  Required Evidence Graphs.
- Primary charts now use required durable historical-cycle and exact durable
  discovery artifacts, not diagnostic or benchmark cycles.
- Added an inline warning when diagnostic/benchmark cycles are present but are
  ignored for required evidence charts.
- Replaced tiny rotated vertical bar labels with horizontal readable chart
  labels and values.
- Tightened chart notes and mobile overflow behavior.

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
- Browser smoke: desktop and 390px mobile Research page loaded with no console
  errors, no page-level horizontal overflow, and the required profitability
  chart selected `r104-btcusdt-durable-public-archive-deep-v1` instead of the
  benchmark-small cycle.
