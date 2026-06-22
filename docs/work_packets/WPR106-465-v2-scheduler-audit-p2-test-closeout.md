# WPR106-465 - V2 Scheduler Audit P2 Test Closeout

Status: self_checked
Audit ID: `V2-AUD-AUTONOMY-014`
Related audit IDs: `V2-AUD-WORKER-024`

## Objective

Close the independent WPR106-463 scheduler audit P2 by adding focused
regressions for the two uncovered blocker cases: missing plan manifest inputs
and `max_jobs_per_plan` budget exhaustion. This is a test/evidence closeout
only; it does not change scheduler behavior, worker behavior, archive data,
or autonomy readiness semantics.

## Allowed Paths

- `docs/work_packets/WPR106-465-v2-scheduler-audit-p2-test-closeout.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
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

- `tests/v2/test_autopilot_scheduler_phase33.py`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR106-465-v2-scheduler-audit-p2-test-closeout.md`

## Decisions Made

- The missing manifest path remains a scheduler-level rejected plan action and
  session blocker.
- The per-plan job cap remains delegated to the bounded cycle runner; the
  scheduler records the runner's blocker output instead of interpreting worker
  internals.
- The WPR106-463 independent audit remains valid with no P0/P1 findings; this
  packet closes the noted P2 coverage gap.

## Acceptance Evidence

- Focused scheduler regressions:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_scheduler_phase33.py -q`
  passed with `6 passed`.
- V2 baseline:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  passed with `319 passed`.
- Compile baseline:
  `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
  passed.
- Contract baseline:
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  passed with `463 passed`.
- Whitespace check:
  `git diff --check` passed.
- No production behavior changed; this packet only adds scheduler blocker
  regressions and ledger/audit closeout documentation.
