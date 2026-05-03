# Work Packet WP11-01 - Promotion Shadow Bridge

Stage: Stage 11 - Promotion pipeline and shadow-only integration
Owner: Orchestrator Agent
Status: closed
Date: 2026-05-03

## Objective

Create the only approved bridge from research artifacts toward runtime review: audited promotion candidates that can be loaded for shadow-only diagnostics and cannot place live orders.

## Scope

- Extend `src/tradingbotsuite/promotion/artifact_validator.py` with `PromotionCandidateManifest` loading and shadow validation.
- Add `src/tradingbotsuite/live/shadow_loader.py` for shadow-only candidate loading and comparison reports.
- Wire `src/tradingbotsuite/runtime.py` to recognize promotion candidate manifests in shadow mode without creating a scorer or execution path.
- Add read-only operator shadow diagnostics through the Research page and API.
- Add live and operator tests for promotion candidate acceptance/rejection, shadow loader reports, and operator-visible diagnostics.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/live -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
```
