# WPR70-01 Operator Research Product Redesign

Stage: R70 operator research product redesign
Owner: Codex Research Agent
Status: closed
Created: 2026-05-06

## Goal

Redesign the operator UI Research tab into a usable product surface for the
current research branch. The page should explain what each run type does, when
to use it, what it tests, where outputs appear, and which controls are safe.
The default flow must focus on provider pipelines, experiment bundles,
historical-cycle review, and evidence inspection instead of presenting older
signal-history tooling as the main research workflow.

## Allowed paths

```text
src/tradingbotsuite/web/templates/research.html
tests/tradingbotsuite/test_operator_ui.py
docs/work_packets/WPR70-01-operator-research-product-redesign.md
docs/stage_reports/STAGE_R70_OPERATOR_RESEARCH_PRODUCT_REDESIGN_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- UI/template and focused operator UI tests only.
- Do not change provider pipeline behavior, experiment runner behavior,
  historical-cycle execution, live execution, promotion behavior, or generated
  evidence.
- Do not add live command endpoints, mode switches, manual-signal controls, or
  smoke-live controls.
- Research outputs must stay `research_only`, `observe_only`, and
  `promotion_ready: false` unless an existing artifact already says otherwise.
- The older signal-history diagnostic endpoints may remain accessible only as
  clearly de-emphasized advanced diagnostics, not as the primary research path.

## Review checklist

- Main UI starts from operator intent and recommended run types.
- Provider stages are explained inline: intake, dataset, evidence, and all.
- Configs are preset-driven with editable advanced paths for power users.
- Page explains what will be tested, where artifacts are written, and what the
  outputs mean.
- Historical-cycle and chart review are prominent and current-branch focused.
- HMM/KNN monitoring, shadow diagnostics, Stage 13 readiness, jobs, and
  artifacts remain visible.
- No live-control endpoints are introduced.

## Exit validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py tests\test_operator_ui.py -q
```

## Close evidence

- Replaced the Research tab with a current-branch Research Control Room that
  starts from operator intent rather than older signal-history tooling.
- Added preset-driven provider pipeline and research experiment controls with
  editable advanced paths.
- Replaced the unexplained provider stage select with explained stage buttons
  for `intake`, `dataset`, `evidence`, and `all`.
- Added historical-cycle review presets with exact
  `run-historical-research-cycle` commands and inline explanations for strategy,
  holding-window, and stability review.
- Kept profitability, candidate mix, gate status, holding-window charts,
  HMM/KNN monitoring, shadow diagnostics, Stage 13 readiness, jobs, and
  artifacts visible.
- Moved older signal-history build/train/calibrate/replay controls into an
  advanced diagnostics section and removed legacy/TradingView language from the
  rendered page.
- Validation passed:
  - `python -m compileall -q src\tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py tests\test_operator_ui.py -q`
    - 43 passed
  - Embedded Research page script parse check passed with Node.
  - `git diff --check`
