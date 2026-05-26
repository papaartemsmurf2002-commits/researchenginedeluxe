# WPR106-10 Exact Discovery Performance-First Worker Cap

Status: complete

## Scope

Restore the exact-discovery default process-worker cap to the faster setting
after operator direction that throughput outweighs instability risk for the
current prolonged study.

## Allowed paths

- `src/tradingbotsuite/research_discovery/runner.py`
- `tests/research_discovery/test_discovery_runner.py`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/work_packets/WPR106-10-exact-discovery-performance-first-worker-cap.md`
- `docs/work_packets/WPR106-09-exact-discovery-full-run-process-pool-crash-followup.md`
- `docs/stage_reports/STAGE_R106_EXACT_DISCOVERY_FULL_RUN_PROCESS_POOL_CRASH_FOLLOWUP_REPORT.md`

## Constraints

- Keep large-resume and zero-trial recovery hardening intact.
- Keep the environment override `TBS_DISCOVERY_REAL_PROCESS_MAX_WORKERS`.
- Preserve research-only, observe-only, and `promotion_ready: false` semantics.
- Do not delete or rewrite active discovery trial records.

## Acceptance

- Default exact-discovery process cap is performance-first again.
- Documentation no longer tells operators that the default is stability-first.
- Focused discovery runner validation passes.

## Closure

`DEFAULT_REAL_DISCOVERY_PROCESS_WORKER_CAP` is restored to 8. The large-resume
state recovery, zero-trial metadata recovery, and partial-ledger protection from
WPR106-09 remain intact. Operators can still lower or raise the cap explicitly
with `TBS_DISCOVERY_REAL_PROCESS_MAX_WORKERS`.

Validation:

- `python -m compileall -q src\tradingbotsuite\research_discovery`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_runner.py::test_real_discovery_process_worker_plan_caps_expanded_fixtures tests\research_discovery\test_discovery_runner.py::test_discovery_runner_large_zero_stop_resume_recovers_lag_without_full_hydration tests\research_discovery\test_discovery_runner.py::test_discovery_runner_zero_stop_real_resume_skips_context_preparation -q`
