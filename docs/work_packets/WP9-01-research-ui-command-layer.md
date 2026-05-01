# Work Packet WP9-01 - Research UI Command Layer

Stage: Stage 9 - Research UI and operator command layer
Owner: Orchestrator Agent
Status: closed
Date: 2026-05-02

## Objective

Add a dedicated research-facing UI and command layer for artifact browsing, experiment comparison, diagnostics, promotion review, and explicit research job queueing.

## Scope

- Add `src/tradingbotsuite/ui/research_app.py`.
- Add research templates under `src/tradingbotsuite/ui/templates/research/`.
- Add `docs/runbooks/research_ui_runbook.md`.
- Add integration coverage in `tests/integration/test_research_ui.py`.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/integration/test_research_ui.py -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py -q
```
