# WPR94-15 Operator UI Truthfulness Modernization

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Modernize the Research tab as a compact operator product surface. The UI must
make research maturity, data readiness, run state, blockers, leads, artifacts,
and routine actions clear without implying live signals or promotion readiness.

## Allowed Paths

- `docs/work_packets/WPR94-15-operator-ui-truthfulness-modernization.md`
- `docs/stage_reports/STAGE_R94_OPERATOR_UI_TRUTHFULNESS_MODERNIZATION_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/OPERATOR_GUIDE.md`
- `docs/OPERATOR_QUICKSTART.md`
- `docs/runbooks/research_ui_runbook.md`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_operator_ui.py`

## Scope

- Remove vague, fluffy, or legacy Research tab wording.
- Use compact labels that distinguish diagnostic, screen-worthy, and
  candidate-ready maturity.
- Surface data readiness, current run, progress, snapshots, blockers, leads,
  charts, artifacts, local run history, and overwrite protection.
- Add or expose routine-action buttons for preflight/readiness, quick/standard
  discovery, pause/stop, resume, snapshots, candidate eligibility, and artifact
  folder navigation where existing routes/contracts support them.
- Avoid empty chart shells; show a clear missing-evidence reason instead.
- Update UI tests and operator docs/runbook for the revised surface.

## Non-Goals

- No backend live trading behavior, live config writes, order placement, runtime
  mode changes, promotion readiness, candidate-pack writing, or sizing logic.
- No new research engine contracts.
- No broad visual rewrite outside the Research tab.

## Validation Plan

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
python -m compileall -q src\tradingbotsuite
git diff --check
```

## Validation Result

Passed on 2026-05-12:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
git diff --check
```

Results:

- Operator UI tests: 35 passed.
- Compileall: passed.
- Contracts: 397 passed.
- Research discovery: 144 passed.
- Diff check: passed with Git CRLF conversion warnings only.

## Exit Evidence

- `src/tradingbotsuite/web/templates/research.html` now includes the Operator
  Board, maturity labels, routine research actions, DOM-visible chart
  missing-evidence reasons, stricter planning/promotion wording, and snapshot /
  discovery-count / intake-readiness handling.
- `tests/tradingbotsuite/test_operator_ui.py` covers the revised labels,
  actions, boundary wording, chart empty-state reasons, snapshot fields, and
  data-readiness artifact references.
- `docs/OPERATOR_GUIDE.md`, `docs/OPERATOR_QUICKSTART.md`, and
  `docs/runbooks/research_ui_runbook.md` document the revised operator surface.
- `docs/stage_reports/STAGE_R94_OPERATOR_UI_TRUTHFULNESS_MODERNIZATION_REPORT.md`
  records closure and validation evidence.
