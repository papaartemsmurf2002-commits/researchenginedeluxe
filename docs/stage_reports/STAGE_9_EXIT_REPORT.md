# Stage 9 Exit Report

Stage: Stage 9 - Research UI and operator command layer
Branch: `research/v3-experimental-engine`
Decision: complete
Date: 2026-05-02
Orchestrator: Codex

## Completed work packets

- WP9-01-research-ui-command-layer

## Validation commands run

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/integration/test_research_ui.py -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py -q
```

## Results

- Research UI integration suite passed, 3 tests.
- Existing operator UI suite passed, 24 tests.

## Artifacts Produced

- `src/tradingbotsuite/ui/research_app.py`
- `src/tradingbotsuite/ui/templates/research/index.html`
- `src/tradingbotsuite/ui/templates/research/artifacts.html`
- `src/tradingbotsuite/ui/templates/research/experiments.html`
- `src/tradingbotsuite/ui/templates/research/jobs.html`
- `docs/runbooks/research_ui_runbook.md`
- `tests/integration/test_research_ui.py`

## Exit Gate

| Requirement | Evidence | Passed |
| --- | --- | --- |
| UI read-only except explicit research job actions | `ResearchUiService.queue_research_job` and route tests | yes |
| Research jobs queued and visible | `/research/api/jobs/run-research-experiment` and `/research/api/jobs` tests | yes |
| Displayed metrics link back to manifests | Experiment page and API tests assert manifest paths | yes |
| No UI route imports live execution adapters | Import-boundary test scans `research_app.py` | yes |

## Carry-Forward

- Stage 10 should harden live preflight and reject research artifacts in live mode before any live branch integration.
