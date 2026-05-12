# WPR97-06 Research UI Fastest Compute Summary

Status: closed
Owner: Codex Research Agent
Stage: R97 aggressive CUDA/TensorCore stability search

## Goal

Make the final R97 `fastest_exact` default visible in the operator Research UI
artifact summary, not only inside raw cycle manifest JSON.

## Allowed Paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/**`
- `docs/work_packets/**`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_operator_ui.py`

## Non-Goals

- Do not change historical-cycle execution logic.
- Do not change live trading behavior, live config, order placement, promotion
  readiness, or sizing logic.
- Do not add GPU speed claims.

## Plan

1. Add historical-cycle compute policy fields to the operator artifact summary.
2. Render compute profile, worker count, aggregate backend, validation backend,
   CUDA selection, and GPU status on the Research artifact card.
3. Add focused operator UI/API coverage.
4. Close with validation.

## Exit Evidence

- Added compute policy and backend summary fields to historical-cycle operator
  artifact summaries.
- Rendered compute profile, workers, backend mix, GPU status, and CUDA selection
  in the Research artifact card.
- Added focused operator API/page coverage.
- Validation recorded in
  `docs/stage_reports/STAGE_R97_RESEARCH_UI_FASTEST_COMPUTE_SUMMARY_REPORT.md`.
