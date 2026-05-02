# Work Packet WP10-01 - Live Preflight Hardening

Stage: Stage 10 - Live branch hardening and preflight enforcement
Owner: Orchestrator Agent
Status: closed
Date: 2026-05-02

## Objective

Move the advisory live-readiness concepts into runtime-enforced live preflight so unsafe live configuration, research jobs, and research-only artifacts fail closed before engine startup or live mode switching.

## Scope

- Add `src/tradingbotsuite/live/preflight.py`.
- Add `src/tradingbotsuite/promotion/artifact_validator.py`.
- Wire live preflight through engine construction, runtime-mode switching, live smoke, canonical CLI, and root launchers.
- Add `tests/live/test_preflight.py`, `tests/live/test_reject_research_artifacts.py`, and `tests/live/test_root_launchers_delegate.py`.
- Document the operator-facing live preflight and testnet smoke path.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_engine.py -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py -q
$env:PYTHONPATH='src'; python -m pytest tests/live -q
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
```

