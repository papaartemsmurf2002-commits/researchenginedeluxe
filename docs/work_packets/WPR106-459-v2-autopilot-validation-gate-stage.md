# WPR106-459 - V2 autopilot validation gate stage

Status: closed
Date: 2026-06-22
Branch: main (workspace branch; stage ledger role: research/v3-experimental-engine)

## Audit IDs

- V2-AUD-AUTONOMY-011
- V2-AUD-VAL-004

## Scope

Make bounded autopilot cycle plans require the durable `validation_gate` worker
stage between vectorized backtest output and ledger/Lead Book interpretation.
Update the generated fixture and public diagnostic cycle specs so validation
manifest refs become required audit evidence.

This chunk does not change validation floors, lockbox policy, coverage floors,
date floors, strategy semantics, ledger append semantics, Lead Book gate
semantics, worker execution semantics, real venue collection behavior, or
readiness claims. It wires the worker-addressable validation gate into the
bounded operational loop.

## Allowed Paths

- docs/work_packets/WPR106-459-v2-autopilot-validation-gate-stage.md
- docs/contracts/autonomy_loop_contract.md
- docs/contracts/worker_job_contract.md
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
- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_fixture_cycle_phase28.py tests/v2/test_autopilot_public_cycle_phase30.py tests/v2/test_validation_worker_phase32.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
- `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- `git diff --check`

## Planned Changes

- Add `validation_gate` to the bounded cycle planner's allowed and required
  stage list.
- Add `validation_manifest_path=` and `validation_manifest_id=` to default
  required audit artifact refs.
- Update generated fixture and public diagnostic cycle specs to declare a
  validation job after vectorized backtest and before ledger/Lead Book.
- Bind the backtest `run_manifest_path=` ref into validation input, keep the
  ledger bound to the same immutable run manifest, and bind validation manifest
  evidence into downstream job input where useful.
- Update contract docs and focused tests to reflect the required validation
  stage.

## Decisions Made

- 2026-06-22: Made `validation_gate` a required bounded autopilot stage rather
  than leaving it as an optional worker kind. This matches the execution brief's
  required order: backtest -> validation -> ledger -> Lead Book -> blocker
  report.
- 2026-06-22: Kept ledger append bound to the immutable backtest
  `run_manifest.json`. The validation job reads the same manifest and writes a
  separate validation gate manifest; the generated audit report requires that
  validation manifest evidence before the loop can pass its blocker report.
- 2026-06-22: Bound `validation_manifest_path` into the ledger job input for
  traceability only. Ledger append semantics were not changed in this packet.
- 2026-06-22: Kept fixture/public cycles `sandbox_diagnostic` and
  non-promotable. Validation gate blockers remain successful blocker evidence,
  not accepted research readiness or strategy-quality proof.

## Changed Files

- docs/ACTIVE_INDEX.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- docs/audit/V2_AUDIT_INDEX.md
- docs/contracts/autonomy_loop_contract.md
- docs/contracts/worker_job_contract.md
- docs/work_packets/WPR106-459-v2-autopilot-validation-gate-stage.md
- src/tradingbotsuite/v2/autonomy/cycle_fixture.py
- src/tradingbotsuite/v2/autonomy/cycle_planner.py
- src/tradingbotsuite/v2/autonomy/cycle_public.py
- tests/v2/test_autopilot_fixture_cycle_phase28.py
- tests/v2/test_autopilot_public_cycle_phase30.py
- tests/v2/test_autopilot_research_cycle_phase26.py
- tests/v2/test_autopilot_research_cycle_runner_phase27.py

## Acceptance Evidence

- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_research_cycle_phase26.py tests/v2/test_autopilot_research_cycle_runner_phase27.py -q`
  passed: 17 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_fixture_cycle_phase28.py tests/v2/test_autopilot_public_cycle_phase30.py tests/v2/test_validation_worker_phase32.py -q`
  passed: 8 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q` passed:
  302 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed:
  463 passed.
- `git diff --check` passed with existing LF-to-CRLF working-copy warnings
  only.
