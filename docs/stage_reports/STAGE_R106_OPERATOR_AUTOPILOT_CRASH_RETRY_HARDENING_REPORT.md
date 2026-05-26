# Stage R106 Operator Autopilot Crash Retry Hardening Report

Date: 2026-05-26
Work packet: `docs/work_packets/WPR106-18-operator-autopilot-crash-retry-hardening.md`

## Scope

Crash/retry hardening for the R106 operator research autopilot. The work stayed
inside research-only operator orchestration and did not add live execution, live
configuration, runtime-mode changes, order placement, candidate-pack writes, or
promotion claims.

## Changes

- Autopilot direct helper steps now retry automatically after a failure.
  - Default: two attempts per step.
  - Internal request override: `max_step_attempts`, bounded from 1 to 5.
- Retry attempts use distinct helper job IDs, for example
  `run-research-autopilot-...-btcusdt-analysis-retry-2`, so a partial output
  directory left by a failed attempt does not make the retry fail immediately.
- Exact-discovery retry keeps the stable-run-id output directory, so if
  `run_state.json` exists the retry resumes instead of restarting from zero.
- Autopilot manifests and job logs now record `retrying`, `failed`, and
  `executed` attempts with attempt number, maximum attempts, helper job id, and
  error detail.
- Operator restart recovery now requeues one stale running
  `run-research-autopilot` job as `...-restart-retry-1`, while marking the
  interrupted original failed for audit history.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_restart_requeues_stale_autopilot_once tests\tradingbotsuite\test_operator_ui.py::test_operator_research_autopilot_retries_failed_step_with_new_attempt_job_id tests\tradingbotsuite\test_operator_ui.py::test_operator_research_autopilot_fails_after_retry_exhaustion -q`
  - `3 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
  - `70 passed`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `427 passed`
- `$env:PYTHONPATH='src'; python -m pytest -q`
  - `1455 passed, 1 skipped`

## Residual State

This reduces transient crash/failure impact but does not make research runs
unbounded or self-healing forever. Persistent failures still fail the autopilot
after bounded attempts and preserve the error in the manifest and job log. No
candidate-ready trading claim exists.
