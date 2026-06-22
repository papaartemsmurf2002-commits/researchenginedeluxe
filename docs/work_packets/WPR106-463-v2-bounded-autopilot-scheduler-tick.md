# WPR106-463 - V2 Bounded Autopilot Scheduler Tick

Status: self_checked
Audit ID: `V2-AUD-AUTONOMY-014`
Related audit IDs: `V2-AUD-WORKER-024`, `V2-AUD-AUDIT-008`

## Objective

Add a run-once, bounded autopilot scheduler tick that can select already
enqueued bounded-cycle plan manifests, execute them through the existing
durable cycle runner under explicit plan/job budgets, and write a research-only
scheduler session manifest with blocker evidence. This closes the gap between
manual `run-cycle-plan` execution and an autonomous manager loop without adding
a daemon, live execution, order/sizing behavior, or readiness claims.

## Allowed Paths

- `docs/work_packets/WPR106-463-v2-bounded-autopilot-scheduler-tick.md`
- `docs/contracts/autonomy_loop_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/autonomy/cycle_scheduler.py`
- `src/tradingbotsuite/v2/autonomy/schemas.py`
- `src/tradingbotsuite/v2/autonomy/__init__.py`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/test_autopilot_scheduler_phase33.py`

## No-Touch Paths

- `src/**/live/**`
- `src/**/runtime.py`
- `run_live_smoke.py`
- `run_manual.py`
- order-placement, broker, exchange-submit, sizing, runtime-config, promotion,
  shadow, and candidate-pack truth-layer paths
- committed `data/research/fixtures/**`
- committed `data/research/historical_cycles/**`
- legacy GUI/operator UI paths
- `src/tradingbot/**`
- `.env`, credential files, local SQLite operator DBs, private caches, and
  unreviewed generated `outputs/**`

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_scheduler_phase33.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Planned Changed Files

- `src/tradingbotsuite/v2/autonomy/cycle_scheduler.py`
- `src/tradingbotsuite/v2/autonomy/schemas.py`
- `src/tradingbotsuite/v2/autonomy/__init__.py`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/test_autopilot_scheduler_phase33.py`
- `docs/contracts/autonomy_loop_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR106-463-v2-bounded-autopilot-scheduler-tick.md`

## Decisions Made

- The scheduler is run-once only. It does not create a daemon, background
  service, timer, network collector, or ASGI/operator in-process job loop.
- The scheduler only consumes already-enqueued bounded-cycle plan manifests.
  Planning, enqueueing, and worker execution semantics stay owned by the
  existing planner and runner.
- Budget exhaustion, missing manifests, non-enqueued plans, and cycle blockers
  are session blockers and not worker-system failures or readiness claims.
- Scheduler manifests preserve the full v2 research-only boundary invariant and
  must keep `accepted_research_ready=false`.

## Acceptance Evidence

- Changed files stayed inside the allowed paths listed above.
- No-touch paths were not edited.
- Focused validation passed:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "& { `$env:PYTHONPATH = 'src'; python -m pytest tests/v2/test_autopilot_scheduler_phase33.py -q }"
# 4 passed in 0.92s
```

- Baseline validation passed:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "& { `$env:PYTHONPATH = 'src'; python -m pytest tests/v2 -q }"
# 313 passed in 27.27s

C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "& { `$env:PYTHONPATH = 'src'; python -m compileall -q src/tradingbotsuite }"
# passed with no output

C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "& { `$env:PYTHONPATH = 'src'; python -m pytest tests/contracts -q }"
# 463 passed in 6.91s

git diff --check
# passed; existing LF-to-CRLF working-tree warnings were reported by Git for
# modified files.
```

- Open blockers: `ISSUE-R106-026` remains the known Python 3.11/full-suite
  parity blocker; this chunk did not change that risk.
- Acceptance status: implemented and self-checked as a bounded run-once
  scheduler tick. The result is not readiness evidence, not a daemon, and not a
  paper/live/order/sizing/promotion surface.
