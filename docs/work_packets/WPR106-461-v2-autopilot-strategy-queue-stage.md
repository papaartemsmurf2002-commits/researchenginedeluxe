# WPR106-461 - V2 autopilot strategy queue stage

Status: closed
Date: 2026-06-22
Branch: main (workspace branch; stage ledger role: research/v3-experimental-engine)

## Audit IDs

- V2-AUD-AUTONOMY-013
- V2-AUD-STRAT-008

## Scope

Make bounded autopilot cycle plans require a durable `strategy_queue_scan`
stage after coverage audit and before vectorized backtest. Update the generated
fixture and public diagnostic cycle specs so declarative strategy specs are
written as local queue inputs, scanned by the durable strategy queue worker,
and bound into the backtest worker through `strategy_spec_file` plus
`strategy_spec_file_sha256`.

This chunk does not change strategy semantics, coverage floors, date floors,
lockbox policy, ledger append semantics, Lead Book gate semantics, worker
execution semantics, real venue collection behavior, or readiness claims. It
wires the existing durable queue worker into the bounded operational loop.

## Allowed Paths

- docs/work_packets/WPR106-461-v2-autopilot-strategy-queue-stage.md
- docs/contracts/autonomy_loop_contract.md
- docs/contracts/worker_job_contract.md
- docs/contracts/strategy_spec_contract.md
- docs/audit/V2_AUDIT_INDEX.md
- docs/ACTIVE_INDEX.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- src/tradingbotsuite/v2/autonomy/cycle_planner.py
- src/tradingbotsuite/v2/autonomy/cycle_fixture.py
- src/tradingbotsuite/v2/autonomy/cycle_public.py
- tests/v2/test_autopilot_research_cycle_phase26.py
- tests/v2/test_autopilot_research_cycle_runner_phase27.py
- tests/v2/test_autopilot_fixture_cycle_phase28.py
- tests/v2/test_autopilot_public_cycle_phase30.py

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
- data/research/fixtures/**
- data/research/historical_cycles/**
- Any credential, lockbox, coverage-floor, date-floor, venue-account, external
  data-licensing, candidate-pack truth-layer, promotion, runtime, or checked
  legacy evidence material

## Expected Tests

- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_research_cycle_phase26.py tests/v2/test_autopilot_research_cycle_runner_phase27.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_fixture_cycle_phase28.py tests/v2/test_autopilot_public_cycle_phase30.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
- `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- `git diff --check`

## Planned Changes

- Add `strategy_queue_scan` to the bounded cycle planner's allowed and
  required stage list between coverage and vectorized backtest.
- Require generated audit evidence for queue manifest refs, accepted spec path,
  accepted spec SHA, and strategy spec hash.
- Enforce required stage order in bounded cycle specs so queue scans cannot be
  declared after backtests.
- Update fixture/public cycle spec writers to write local declarative strategy
  spec files, declare a `strategy_queue_scan` job, remove inline backtest specs,
  and bind queue output refs into the backtest input spec.
- Update focused planner/runner/fixture/public tests and contracts.

## Decisions Made

- 2026-06-22: Made `strategy_queue_scan` a required bounded-cycle stage rather
  than an optional worker kind. This matches the execution brief's required
  strategy-spec queue scan and validation step before backtesting.
- 2026-06-22: Enforced required-stage ordering in the planner so declared
  cycles cannot put strategy queue scans after backtests or otherwise drift
  from the operational loop order.
- 2026-06-22: Updated generated fixture and public diagnostic cycle specs to
  write local declarative strategy JSON files, scan them with
  `require_single_accepted=true`, and bind `accepted_spec_path` plus
  `accepted_spec_sha256` into backtests.
- 2026-06-22: Removed inline generated backtest strategy specs from fixture and
  public cycle specs. Durable backtests now receive strategy specs through the
  same trusted file-intake seam as user-provided queue specs.
- 2026-06-22: Kept fixture/public cycles `sandbox_diagnostic` and
  non-promotable. Strategy queue evidence remains input hygiene and worker-chain
  evidence only, not strategy-performance or readiness proof.

## Changed Files

- docs/ACTIVE_INDEX.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- docs/audit/V2_AUDIT_INDEX.md
- docs/contracts/autonomy_loop_contract.md
- docs/contracts/strategy_spec_contract.md
- docs/contracts/worker_job_contract.md
- docs/work_packets/WPR106-461-v2-autopilot-strategy-queue-stage.md
- src/tradingbotsuite/v2/autonomy/cycle_fixture.py
- src/tradingbotsuite/v2/autonomy/cycle_planner.py
- src/tradingbotsuite/v2/autonomy/cycle_public.py
- tests/v2/test_autopilot_fixture_cycle_phase28.py
- tests/v2/test_autopilot_public_cycle_phase30.py
- tests/v2/test_autopilot_research_cycle_phase26.py
- tests/v2/test_autopilot_research_cycle_runner_phase27.py

## Acceptance Evidence

- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_research_cycle_phase26.py tests/v2/test_autopilot_research_cycle_runner_phase27.py tests/v2/test_autopilot_fixture_cycle_phase28.py tests/v2/test_autopilot_public_cycle_phase30.py -q`
  passed: 23 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q` passed:
  307 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed:
  463 passed.
- `git diff --check` passed with existing LF-to-CRLF working-copy warnings
  only.
