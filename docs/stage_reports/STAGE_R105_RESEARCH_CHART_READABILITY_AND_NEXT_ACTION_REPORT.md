# Stage R105 Research Chart Readability And Next Action Report

Date: 2026-05-20
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR105-103-research-chart-readability-and-next-action.md`

## Scope

This UI-only pass fixes the unreadable Research tab chart section and prevents
diagnostic or benchmark historical-cycle artifacts from being presented as the
primary required evidence chart.

## Changes

- Renamed the section to Required Evidence Profitability Chart and Required
  Evidence Graphs.
- Primary chart selection now prefers required durable historical-cycle and
  exact durable discovery artifacts.
- Diagnostic, smoke, compatibility, and benchmark cycles are excluded from the
  primary required charts.
- The chart renderer now uses horizontal bars with readable labels and values
  instead of tiny rotated axis labels.
- Chart notes now state when required durable evidence is missing and point the
  operator back to the checklist.
- Mobile layout remains bounded with charts visible and no page-level
  horizontal overflow.

## Boundary

- This did not change research-cycle, discovery, backtest, feature, gate, or
  scoring semantics.
- This did not add live execution, live config writes, runtime-mode mutation,
  order placement, promotion behavior, candidate-pack writing, or sizing
  behavior.

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
- Browser smoke: desktop and 390px mobile Research page loaded, no console
  errors, no page-level horizontal overflow, and the required profitability
  chart selected `r104-btcusdt-durable-public-archive-deep-v1` instead of the
  benchmark-small cycle.
