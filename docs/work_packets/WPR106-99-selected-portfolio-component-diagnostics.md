# WPR106-99 Selected Portfolio Component Diagnostics

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Diagnose the WPR106-98 selected pre-May portfolio robustness leads at component
level. Determine whether the remaining losing-month instability is driven by a
specific sleeve, symbol, side, regime, volatility bucket, month cluster, or
overlap pattern, and use May 2026 only as a post-selection benchmark view.

## Scope

- Use WPR106-98 selected leads as fixed pre-May-selected inputs.
- Load original pre-May sleeve trade artifacts from the WPR106-95 sleeve
  universe.
- Load WPR106-97 May sleeve trades only after component diagnostics are
  computed.
- Write deterministic diagnostics for:
  - sleeve-level contribution by month and year;
  - annual losing-month concentration;
  - largest positive and negative monthly contributors;
  - side, regime, and volatility-bucket contribution;
  - leave-one-out and subset portfolio ablations selected by pre-May evidence;
  - May benchmark behavior for the same fixed component/subset definitions.
- Keep all outputs research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-99-selected-portfolio-component-diagnostics.md`
- `docs/stage_reports/STAGE_R106_SELECTED_PORTFOLIO_COMPONENT_DIAGNOSTICS_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_99*/**`

## Out of scope

- No strategy, feature, filter, threshold, parameter, optimizer, or execution
  retuning using May 2026.
- No new strategy, feature, research-cycle, backtest, live-boundary, or
  operator UI code.
- No candidate pack, promotion artifact, paper/live artifact, order placement,
  position sizing, runtime-mode change, live-configuration write, or CUDA
  speedup claim.
- No synthetic fallback data.

## Exit evidence

- Component diagnostics and subset ablation artifacts are written under
  `data/research/wpr106_99*/`.
- May benchmark joins are clearly marked post-selection and not used to tune
  component definitions.
- Stage report records the instability source, benchmark-only May outcome,
  and next research direction.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

Completed:

- Runner:
  `data/research/wpr106_99_selected_portfolio_component_diagnostics/scripts/run_wpr106_99_component_diagnostics.py`
- Summary:
  `data/research/wpr106_99_selected_portfolio_component_diagnostics/wpr106_99_component_diagnostics_summary.json`
- Pre-May component diagnostics:
  `data/research/wpr106_99_selected_portfolio_component_diagnostics/pre_may/`
- May benchmark-only diagnostics:
  `data/research/wpr106_99_selected_portfolio_component_diagnostics/may_benchmark/`
- Stage report:
  `docs/stage_reports/STAGE_R106_SELECTED_PORTFOLIO_COMPONENT_DIAGNOSTICS_REPORT.md`
- Validation passed:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` with 460 passed.
