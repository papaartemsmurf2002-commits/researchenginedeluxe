# WPR106-18 Operator Autopilot Crash Retry Hardening

Status: closed

## Scope

Harden the R106 operator research autopilot so transient step failures during a
long run are retried automatically with clear attempt evidence before the
autopilot is marked failed or blocked.

This packet does not add new research capability, does not claim candidate-ready
performance, and does not promote any artifact beyond research-only analysis.

## Allowed paths

- `src/tradingbotsuite/operator_console.py`
- `tests/tradingbotsuite/test_operator_ui.py`
- `docs/work_packets/WPR106-18-operator-autopilot-crash-retry-hardening.md`
- `docs/stage_reports/STAGE_R106_OPERATOR_AUTOPILOT_CRASH_RETRY_HARDENING_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Constraints

- Preserve `research_only`, `observe_only`, and `promotion_ready: false`.
- Do not place orders, change live runtime mode, write live configuration, or
  import live order-placement adapters into research code.
- Keep retry behavior bounded and visible in the autopilot manifest.
- Preserve exact-discovery resume semantics and avoid overwriting partial
  attempt outputs.

## Acceptance

- Autopilot retries failed direct helper steps automatically up to a bounded
  per-step attempt limit.
- Each failed attempt is recorded in the autopilot manifest and operator job
  log with enough detail to diagnose the failure.
- Retry attempts use distinct helper job IDs so a partial output directory from
  a failed attempt does not make the retry fail immediately.
- Focused operator tests cover retry success and retry exhaustion.

## Exit summary

- Added bounded per-step autopilot retries. The default is two attempts per
  direct helper step, capped at five when requested internally through
  `max_step_attempts`.
- Retry attempts use attempt-specific helper job IDs such as
  `...-retry-2`, so partial output directories from failed analysis, delta,
  exit-lab, catalog, cycle, or eligibility attempts do not poison the retry.
- Exact-discovery retries preserve stable-run-id resume semantics, so a retry
  after a partial discovery run can resume from `run_state.json`.
- Autopilot manifests and operator job logs now record retrying, failed, and
  executed attempts with attempt number, maximum attempts, helper job id, and
  error detail.
- Operator restart recovery now requeues one stale running
  `run-research-autopilot` job with a restart-retry job id, while marking the
  interrupted original failed for auditability.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_restart_requeues_stale_autopilot_once tests\tradingbotsuite\test_operator_ui.py::test_operator_research_autopilot_retries_failed_step_with_new_attempt_job_id tests\tradingbotsuite\test_operator_ui.py::test_operator_research_autopilot_fails_after_retry_exhaustion -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
- `$env:PYTHONPATH='src'; python -m pytest -q`
