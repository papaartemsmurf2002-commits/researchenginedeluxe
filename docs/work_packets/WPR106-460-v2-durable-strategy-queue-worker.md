# WPR106-460 - V2 durable strategy queue worker

Status: closed
Date: 2026-06-22
Branch: main (workspace branch; stage ledger role: research/v3-experimental-engine)

## Audit IDs

- V2-AUD-AUTONOMY-012
- V2-AUD-BTENG-007
- V2-AUD-STRAT-007
- V2-AUD-WORKER-023

## Scope

Make the existing local strategy-spec queue scanner durable-worker addressable,
and add trusted strategy-spec file intake for durable vectorized backtest jobs
only when the spec file is local, declarative, supported by the validator, and
SHA-256 checked by the job spec.

This chunk does not make strategy queue scanning a required bounded-cycle
stage. It creates the worker and file-intake seam needed for a later bounded
cycle packet to bind queue-normalized spec files into backtests. It does not
change strategy semantics, coverage floors, date floors, lockbox policy,
ledger semantics, Lead Book semantics, real venue collection behavior, or
readiness claims.

## Allowed Paths

- docs/work_packets/WPR106-460-v2-durable-strategy-queue-worker.md
- docs/contracts/autonomy_loop_contract.md
- docs/contracts/backtest_engine_contract.md
- docs/contracts/strategy_spec_contract.md
- docs/contracts/worker_job_contract.md
- docs/audit/V2_AUDIT_INDEX.md
- docs/ACTIVE_INDEX.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- src/tradingbotsuite/v2/autonomy/__init__.py
- src/tradingbotsuite/v2/autonomy/strategy_queue.py
- src/tradingbotsuite/v2/backtest_engine/jobs.py
- src/tradingbotsuite/v2/workers/models.py
- src/tradingbotsuite/v2/workers/runner.py
- tests/v2/test_autopilot_strategy_queue_phase31.py
- tests/v2/test_workers_phase7.py

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

- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_strategy_queue_phase31.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
- `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- `git diff --check`

## Planned Changes

- Add a `strategy_queue_scan` worker kind and route it through the durable
  worker runner.
- Let the worker run the existing strategy queue scanner and surface the queue
  manifest, manifest hash, accepted/rejected counts, blockers, and exactly-one
  accepted spec refs when available.
- Add optional `require_single_accepted` queue-scan policy so worker callers
  can fail closed with blocker evidence when a downstream backtest expects one
  bound spec.
- Add SHA-checked `strategy_spec_file` intake for durable vectorized backtest
  jobs while preserving inline declarative specs.
- Reject missing SHA, SHA mismatch, unsupported/secret-like paths, simultaneous
  inline/file specs, and invalid declarative spec files before any panel load
  or run artifact write.
- Update contracts and focused tests for the durable queue worker and trusted
  backtest file intake.

## Decisions Made

- 2026-06-22: Added `strategy_queue_scan` as a durable worker kind but did not
  make it a required bounded-cycle stage in this packet. The next planner
  packet can bind its accepted spec refs into backtests without mixing worker
  plumbing and loop-order policy.
- 2026-06-22: Made `require_single_accepted` emit blocker evidence for
  multiple accepted specs and intentionally withheld `accepted_spec_path` when
  the queue is ambiguous. Downstream jobs must not infer which spec to run.
- 2026-06-22: Allowed durable backtests to load local JSON/YAML
  `strategy_spec_file` inputs only with a matching `strategy_spec_file_sha256`;
  missing or mismatched hashes fail before panel load or run artifact writes.
- 2026-06-22: Kept inline `strategy_spec` intake for compatibility and reject
  job specs that provide both inline and file inputs.
- 2026-06-22: Used a lazy worker-runner import for the strategy queue handler
  after focused validation exposed a runner/autonomy package import cycle.

## Changed Files

- docs/ACTIVE_INDEX.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- docs/audit/V2_AUDIT_INDEX.md
- docs/contracts/autonomy_loop_contract.md
- docs/contracts/backtest_engine_contract.md
- docs/contracts/strategy_spec_contract.md
- docs/contracts/worker_job_contract.md
- docs/work_packets/WPR106-460-v2-durable-strategy-queue-worker.md
- src/tradingbotsuite/v2/autonomy/__init__.py
- src/tradingbotsuite/v2/autonomy/strategy_queue.py
- src/tradingbotsuite/v2/backtest_engine/jobs.py
- src/tradingbotsuite/v2/workers/models.py
- src/tradingbotsuite/v2/workers/runner.py
- tests/v2/test_autopilot_strategy_queue_phase31.py
- tests/v2/test_workers_phase7.py

## Acceptance Evidence

- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_strategy_queue_phase31.py -q`
  passed: 6 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py -q`
  passed: 53 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_strategy_queue_phase31.py tests/v2/test_workers_phase7.py -q`
  passed: 59 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q` passed:
  306 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed:
  463 passed.
- `git diff --check` passed with existing LF-to-CRLF working-copy warnings
  only.
