# WPR106-453 - V2 autopilot cycle output-ref bindings

Status: closed
Date: 2026-06-21
Branch: research/v3-experimental-engine

## Audit IDs

- V2-AUD-AUTONOMY-007
- V2-AUD-WORKER-020

## Scope

Add bounded, planner-declared output-ref bindings so an enqueued autopilot
cycle can pass IDs and artifact paths from earlier successful worker jobs into
later still-queued planned jobs before execution.

This chunk must preserve the research-only boundary. It must not add daemon
behavior, venue fetching outside durable workers, readiness certification,
candidate/promotion evidence, paper/live/order/sizing/runtime behavior, or
coverage-floor/date-floor/lockbox policy changes.

## Allowed Paths

- docs/work_packets/WPR106-453-v2-autopilot-cycle-output-ref-bindings.md
- docs/contracts/autonomy_loop_contract.md
- docs/contracts/worker_job_contract.md
- docs/audit/V2_AUDIT_INDEX.md
- docs/ACTIVE_INDEX.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- src/tradingbotsuite/v2/autonomy/schemas.py
- src/tradingbotsuite/v2/autonomy/cycle_planner.py
- src/tradingbotsuite/v2/autonomy/cycle_runner.py
- src/tradingbotsuite/v2/workers/job_store.py
- tests/v2/test_autopilot_research_cycle_phase26.py
- tests/v2/test_autopilot_research_cycle_runner_phase27.py

## No-Touch Paths

- src/tradingbotsuite/live/**
- src/tradingbotsuite/runtime/**
- src/tradingbotsuite/execution/**
- src/tradingbotsuite/order*
- src/tradingbotsuite/broker*
- config/live/**
- config/paper/**
- data/live/**
- data/credentials/**
- Any credential, lockbox, or venue-account material

## Expected Tests

- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_research_cycle_phase26.py tests/v2/test_autopilot_research_cycle_runner_phase27.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
- `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- `git diff --check`

## Planned Changes

- Add an autopilot cycle binding schema with source job ID, target job ID,
  target input-spec path, and source output-ref prefix.
- Validate bindings during planning: known jobs only, source dependency must
  precede target dependency, generated audit jobs are not binding targets, and
  target input paths may not touch research-boundary flags.
- Persist bindings in the cycle plan manifest and identity.
- Add a queued-only worker-store method that updates input spec, recomputes the
  hash, and records a same-status transition for auditability.
- Apply bindings in the cycle runner before running each queued planned job.
  Missing source refs, unsucceeded sources, ambiguous refs, or unsafe updates
  must become blockers.

## Decisions Made

- 2026-06-21: Bindings are explicit plan data, not inferred from worker kinds.
  This keeps the feature reversible and avoids hidden coupling to current
  worker output names.
- 2026-06-21: Bindings are applied only to queued jobs. Already-succeeded jobs
  are not mutated, and claimed/running/terminal jobs block instead of being
  changed.
- 2026-06-21: Ref resolution fails closed when a source job has zero or
  multiple distinct matching ref values for the requested prefix.
- 2026-06-21: The runner revalidates binding declarations from the loaded plan
  manifest before running any worker job, so tampered or stale manifests fail
  closed even if the original planner validation was bypassed.

## Changed Files

- docs/work_packets/WPR106-453-v2-autopilot-cycle-output-ref-bindings.md
- docs/contracts/autonomy_loop_contract.md
- docs/contracts/worker_job_contract.md
- docs/audit/V2_AUDIT_INDEX.md
- docs/ACTIVE_INDEX.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- src/tradingbotsuite/v2/autonomy/schemas.py
- src/tradingbotsuite/v2/autonomy/cycle_planner.py
- src/tradingbotsuite/v2/autonomy/cycle_runner.py
- src/tradingbotsuite/v2/workers/job_store.py
- tests/v2/test_autopilot_research_cycle_phase26.py
- tests/v2/test_autopilot_research_cycle_runner_phase27.py

## Acceptance Evidence

- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_research_cycle_phase26.py tests/v2/test_autopilot_research_cycle_runner_phase27.py -q`
  passed: 17 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q` passed: 285 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed:
  463 passed.
- `git diff --check` passed with existing LF-to-CRLF working-copy warnings
  only.
