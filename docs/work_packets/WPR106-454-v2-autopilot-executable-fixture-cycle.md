# WPR106-454 - V2 autopilot executable fixture cycle

Status: closed
Date: 2026-06-21
Branch: main (workspace branch; stage ledger role: research/v3-experimental-engine)

## Audit IDs

- V2-AUD-AUTONOMY-008
- V2-AUD-WORKER-021

## Scope

Add a canonical, sandbox-diagnostic fixture cycle spec writer that proves the
bounded durable autopilot chain can execute through existing worker handlers:
universe refresh, archive write, coverage audit, vectorized backtest, ledger
append/export, Lead Book upsert, and generated audit report.

This chunk must not claim accepted research readiness. Fixture cycles are
operational wiring evidence only. They must remain research-only,
observe-only, promotion-ready false, sandbox diagnostic, and non-candidate.
They must not add daemon scheduling, background services, live/paper/order/
sizing/runtime behavior, candidate packs, promotion language, credential use,
policy-floor changes, or real venue data-licensing decisions.

## Allowed Paths

- docs/work_packets/WPR106-454-v2-autopilot-executable-fixture-cycle.md
- docs/contracts/autonomy_loop_contract.md
- docs/contracts/worker_job_contract.md
- docs/audit/V2_AUDIT_INDEX.md
- docs/ACTIVE_INDEX.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- src/tradingbotsuite/v2/autonomy/cycle_fixture.py
- src/tradingbotsuite/v2/autonomy/__init__.py
- src/tradingbotsuite/v2/cli/main.py
- tests/v2/test_autopilot_fixture_cycle_phase28.py

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
- Any credential, lockbox, coverage-floor, date-floor, or venue-account
  material

## Expected Tests

- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_fixture_cycle_phase28.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_research_cycle_phase26.py tests/v2/test_autopilot_research_cycle_runner_phase27.py tests/v2/test_autopilot_fixture_cycle_phase28.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
- `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- `git diff --check`

## Planned Changes

- Add a fixture cycle config/result API that writes bounded fixture inputs and
  a valid `autopilot_bounded_cycle_spec_v1` JSON file.
- Generate fixture market data for one eligible Hyperliquid BTC perpetual over
  a seven-month 2024+ daily window, with all generated artifacts under the
  requested output root.
- Declare output-ref bindings from universe and archive jobs into coverage and
  backtest jobs, from backtest into ledger, and from ledger into Lead Book.
- Add an autopilot CLI command that writes the fixture cycle spec and prints
  all follow-on paths without enqueueing or running jobs.
- Add an executable test that plans, enqueues, and runs the generated fixture
  cycle through actual durable worker handlers, then verifies the audit report,
  ledger, Lead Book, execution manifest, and research boundary flags.
- Document that this fixture is a loop-operability proof only, not accepted
  research evidence or autonomous-ready certification.

## Decisions Made

- 2026-06-21: The generated fixture cycle uses `sandbox_diagnostic` evidence
  mode because collector-produced fixture data and generated local fixtures are
  not accepted research evidence.
- 2026-06-21: The generated backtest cost model explicitly uses
  `funding_required=false` and `funding_missing_policy=explicit_zero` because
  the candle-only fixture archive does not include funding rows. This is
  documented in the generated spec and Lead Book blockers.
- 2026-06-21: The fixture strategy removes coverage-ratio and spread filters
  from the built-in mean-reversion example so the generated silver bars remain
  compatible with existing archive normalization schemas.
- 2026-06-21: The generated cycle omits nested strategy/cost boundary keys from
  job input specs because the bounded-cycle planner rejects any boundary-key
  override inside worker input specs. The strategy schema still defaults and
  validates the research-only invariant when the backtest worker parses the
  inline strategy spec.
- 2026-06-21: The generated Lead Book row keeps the fixture's low-trade-count
  gate failure visible. `minimum_five_trades_per_month_failed` is acceptable
  blocker evidence for this fixture because the cycle is an operability proof,
  not a research-performance lead.

## Changed Files

- docs/ACTIVE_INDEX.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- docs/audit/V2_AUDIT_INDEX.md
- docs/contracts/autonomy_loop_contract.md
- docs/contracts/worker_job_contract.md
- docs/work_packets/WPR106-454-v2-autopilot-executable-fixture-cycle.md
- src/tradingbotsuite/v2/autonomy/__init__.py
- src/tradingbotsuite/v2/autonomy/cycle_fixture.py
- src/tradingbotsuite/v2/cli/main.py
- tests/v2/test_autopilot_fixture_cycle_phase28.py

## Acceptance Evidence

- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_fixture_cycle_phase28.py -q`
  passed: 2 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_research_cycle_phase26.py tests/v2/test_autopilot_research_cycle_runner_phase27.py tests/v2/test_autopilot_fixture_cycle_phase28.py -q`
  passed: 19 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q` passed: 287 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed:
  463 passed.
- `git diff --check` passed with existing LF-to-CRLF working-copy warnings for
  touched files only.
- The executable fixture test generated a bounded cycle, planned and enqueued
  seven jobs including the generated audit job, executed all jobs through real
  durable worker handlers, appended one sandbox ledger row, upserted one
  non-promotable Lead Book row, and verified the final audit report completed
  with expected sandbox/missing-real-evidence blockers instead of readiness
  claims.
