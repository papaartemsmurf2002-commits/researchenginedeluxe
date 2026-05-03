# Work Packet WP13-01 - Stage 13 Readiness Planning And Offline Verifiers

Stage: Stage 13 readiness planning only
Substages: Stage 13 evidence, shadow/paper review, testnet validation, rollback readiness
Owner: Orchestrator Agent
Status: closed - execution blocked pending human evidence and approval
Date: 2026-05-03

## Objective

Add the automatable readiness layer that can prepare Stage 13 evidence schemas and offline validators without running live, paper, shadow, or testnet execution.

## Scope

- Add `PaperRunManifest`, `ShadowRunArchiveManifest`, `TestnetValidationManifest`, and `Stage13ReadinessReport`.
- Add `plan-stage13-readiness` to write templates, a blocked readiness report, and rollback/operator checklists.
- Validate Stage 12 OOS/stress evidence floors without accepting in-sample or synthetic-only evidence.
- Validate Stage 13 paper, shadow, testnet, human-approval, rollback, asset-scope, and execution-journal evidence offline.
- Add read-only operator diagnostics for Stage 13 readiness.
- Centralize the research command registry and ensure all research commands are rejected by live preflight.

## Non-Scope

- No paper, shadow, testnet, or live runtime is started.
- No Hyperliquid calls are made.
- No runtime mode switches, sizing controls, or order controls are exposed by the readiness diagnostics.
- No generated template marks a strategy promotion-ready.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_stage13_readiness.py tests/tradingbotsuite/test_operator_ui.py -q
$env:PYTHONPATH='src'; python -m pytest tests/live -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m tradingbotsuite.main plan-stage13-readiness --help
$env:PYTHONPATH='src'; python -m tradingbotsuite.main plan-stage13-readiness --output-dir "$env:TEMP\stage13-readiness-smoke"
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
```

## Exit Criteria

The work packet exits when Stage 13 readiness templates and offline verifiers are reproducible, live mode rejects the new research command, and the operator UI exposes only read-only readiness status. Stage 13 execution remains blocked until real paper/shadow/testnet archives and explicit human approval exist.
