# Stage R105 Research UI Required Workflow Clarity Report

Date: 2026-05-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR105-102-research-ui-required-workflow-clarity.md`

## Scope

This UI-only pass reduces Research tab crowding and makes the required
operator path explicit. It does not change research-cycle, discovery, backtest,
feature, scoring, gate, promotion, live-runtime, order-placement, or sizing
behavior.

## Changes

- The top Research tab section is now the Required Evidence Checklist with
  explicit copy stating that this checklist is the only required run path.
- Required action buttons are grouped as durable input check, BTC evidence
  path, ETH mirror evidence, and candidate eligibility review.
- Manual controls are split into Required Manual Presets and Optional
  Diagnostics And Legacy Compatibility.
- Provider pipeline diagnostics, HMM/KNN research experiments, and hardware
  utilization benchmark controls are secondary diagnostic controls behind a
  disclosure.
- Stale operator-facing labels such as R104 Command Center and R104 Durable
  Discovery Run were removed. Internal R104 spec paths remain internal
  references only.
- Dynamic recommended defaults now format internal R104 scope as the current
  durable public-archive fixture set.
- Mobile layout wraps long paths and status values, keeps tables inside
  scroll containers, and prevents page-level horizontal overflow with
  diagnostics open.

## Boundary

- Research outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.
- No live execution, live config writes, runtime-mode mutation, order
  placement, promotion behavior, candidate-pack writing, or sizing behavior
  was added.

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
- Browser smoke: desktop and 390px mobile Research page loaded, optional
  diagnostics opened, no console errors on a fresh session, stale R104
  operator headings absent, and no page-level horizontal overflow.
