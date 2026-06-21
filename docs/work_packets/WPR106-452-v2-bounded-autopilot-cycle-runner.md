# WPR106-452 - V2 Bounded Autopilot Cycle Runner

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-AUTONOMY-006`
- `V2-AUD-WORKER-019`
- `V2-AUD-AUDIT-005`

## Objective

Add a bounded research-cycle executor for an already enqueued WPR106-451 plan.
The executor may run planned durable jobs in declared dependency order, skip
already successful planned jobs, and run the generated final `audit_check` job
to write the blocker report. It must stay finite, explicit, and operator-run;
it is not a scheduler daemon, continuous collector, venue fetch shortcut, or
autonomous-ready certification surface.

This chunk advances the operational loop plumbing only. It must not change
coverage floors, lockbox rules, date floors, universe policy, data licensing,
credential handling, candidate/promotion language, or legacy evidence.

## Allowed Paths

- `docs/work_packets/WPR106-452-v2-bounded-autopilot-cycle-runner.md`
- `docs/contracts/autonomy_loop_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/contracts/audit_report_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/autonomy/__init__.py`
- `src/tradingbotsuite/v2/autonomy/schemas.py`
- `src/tradingbotsuite/v2/autonomy/cycle_runner.py`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/test_autopilot_research_cycle_runner_phase27.py`

## No-Touch Paths

- `src/**/live/**`
- `src/**/runtime.py`
- order placement, broker, execution adapter, sizing, and live config paths
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `src/tradingbotsuite/promotion/**`
- `src/tradingbotsuite/live/shadow_loader.py`
- committed legacy evidence under `data/research/**`
- legacy GUI paths
- `.env`, credential files, local SQLite operator DBs outside temporary test
  roots, and unreviewed `outputs/**`

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_research_cycle_phase26.py tests/v2/test_autopilot_research_cycle_runner_phase27.py tests/v2/test_cli_smoke.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Acceptance Criteria

- An enqueued plan manifest can be loaded and rejected if it is only
  `planned`, lacks a job store path, or points at a different requested job
  store.
- The executor runs planned queued jobs only when the planned job is the next
  queued job for its worker kind, preventing accidental execution of unrelated
  queued jobs.
- Already successful planned jobs are recorded as skipped and remain valid loop
  evidence for the final audit report.
- Failed, missing, incomplete, out-of-order, or not-next planned jobs become
  explicit execution blockers; the final generated `audit_check` job is still
  attempted when safe so blockers are reported.
- The executor writes an `autopilot_cycle_execution.json` manifest with the
  canonical research-only invariant, `accepted_research_ready=false`, and
  `promotion_ready=false`.
- The CLI prints execution manifest, status, executed job count, blocker count,
  audit report path, and non-readiness boundary flags.
- No daemon loop, venue API call, WebSocket stream, accepted coverage proof,
  candidate pack, paper/live signal, order placement, sizing instruction,
  runtime-mode change, or promotion behavior is added.

## Changed Files

Planned:

- `docs/work_packets/WPR106-452-v2-bounded-autopilot-cycle-runner.md`
- `docs/contracts/autonomy_loop_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/contracts/audit_report_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/autonomy/__init__.py`
- `src/tradingbotsuite/v2/autonomy/schemas.py`
- `src/tradingbotsuite/v2/autonomy/cycle_runner.py`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/test_autopilot_research_cycle_runner_phase27.py`

## Decisions Made

- Use an operator-invoked bounded executor for a stored plan, not a scheduler
  daemon or continuous capture controller.
- Reuse durable worker jobs and the generated `audit_check` worker instead of
  adding a second blocker-report format.
- Guard `run_one_job` by verifying the planned job is the next queued job of
  its kind before calling the kind-based worker runner.
- Treat successful prior jobs as replayable evidence and failed/incomplete
  prior jobs as blockers, without mutating their terminal records.

## Acceptance Evidence

Focused validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_research_cycle_phase26.py tests/v2/test_autopilot_research_cycle_runner_phase27.py tests/v2/test_cli_smoke.py -q
# 14 passed
```

Broader validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
# 279 passed

$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
# 463 passed

git diff --check
# passed with existing LF-to-CRLF warnings on touched files only
```

The new runner was validated on temporary job stores only. It does not prove
real Hyperliquid historical archive coverage, unattended scheduler operation,
independent audit acceptance, or autonomous-ready release status.

## No-Touch Review

- No live, runtime, order-placement, broker, sizing, promotion, candidate-pack,
  legacy GUI, or committed legacy evidence paths were changed.
- The new CLI subcommand runs only an already enqueued durable plan through the
  existing worker runner and generated final audit job. It does not call venue
  APIs directly, open WebSockets directly, write live configuration, place
  orders, write sizing instructions, create candidate/promotion artifacts, or
  change data floors.
- Execution manifests and generated audit reports are operational blocker
  evidence only. They keep `accepted_research_ready=false` and
  `promotion_ready=false`.
