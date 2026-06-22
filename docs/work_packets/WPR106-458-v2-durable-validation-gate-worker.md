# WPR106-458 - V2 durable validation gate worker

Status: closed
Date: 2026-06-22
Branch: main (workspace branch; stage ledger role: research/v3-experimental-engine)

## Audit IDs

- V2-AUD-VAL-003
- V2-AUD-WORKER-022

## Scope

Add a research-only durable `validation_gate` worker stage that consumes a
completed v2 `run_manifest.json`, inspects its fold and cost-stress artifacts,
and writes a deterministic validation gate manifest with pass/fail blockers.

This chunk does not change validation floors, lockbox policy, coverage floors,
date floors, strategy semantics, ledger append semantics, Lead Book behavior,
autopilot cycle requirements, or readiness claims. It makes validation a
worker-addressable loop stage so later bounded-cycle packets can place it
between backtest and ledger.

## Allowed Paths

- docs/work_packets/WPR106-458-v2-durable-validation-gate-worker.md
- docs/contracts/validation_contract.md
- docs/contracts/worker_job_contract.md
- docs/audit/V2_AUDIT_INDEX.md
- docs/ACTIVE_INDEX.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- src/tradingbotsuite/v2/validation/jobs.py
- src/tradingbotsuite/v2/validation/__init__.py
- src/tradingbotsuite/v2/workers/models.py
- src/tradingbotsuite/v2/workers/runner.py
- tests/v2/test_validation_worker_phase32.py

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
- Any credential, lockbox, coverage-floor, date-floor, venue-account, or
  checked legacy evidence material

## Expected Tests

- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_validation_worker_phase32.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_validation_phase14.py tests/v2/test_validation_worker_phase32.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
- `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- `git diff --check`

## Planned Changes

- Add `validation_gate` to durable worker job kinds and route it through the
  worker runner.
- Add a validation worker handler that reads local run artifacts only, writes
  `validation_gate_manifest.json`, and records blocker reasons for failed run
  status, non-pass validation status, pre-2024 starts, under-six-month windows,
  low coverage, accepted current-universe evidence, lockbox overlap, missing
  cost-stress scenarios, and weak fold stability.
- Preserve the full canonical research-only boundary on validation gate
  outputs.
- Reject secret-like or unsupported validation output paths before writing.
- Add focused tests for a passing run, a blocked run, and unsafe output path
  rejection.

## Decisions Made

- Implemented `validation_gate` as a durable worker kind and runner route,
  not as an autopilot planner requirement yet. Later packets can place this
  stage into fixture/public/real cycle specs without changing the gate itself.
- Wrote validation gate manifests beside the source `run_manifest.json` by
  default and required any explicit report path to remain inside that run
  directory.
- Treated validation blockers as successful worker output. Invalid inputs,
  missing/escaped artifacts, artifact hash mismatches, and secret-like report
  paths remain worker failures.
- Used existing run-manifest, fold-metric, and cost-stress artifacts only; the
  worker does not fetch data, rerun backtests, mutate run manifests, append
  ledgers, or update Lead Book rows.
- Preserved existing floors and policy values: 2024 start floor, six usable
  months, 0.98 coverage, as-of universe for accepted evidence, and lockbox
  overlap rejection.

## Changed Files

- docs/work_packets/WPR106-458-v2-durable-validation-gate-worker.md
- docs/contracts/validation_contract.md
- docs/contracts/worker_job_contract.md
- docs/audit/V2_AUDIT_INDEX.md
- docs/ACTIVE_INDEX.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- src/tradingbotsuite/v2/validation/jobs.py
- src/tradingbotsuite/v2/validation/__init__.py
- src/tradingbotsuite/v2/workers/models.py
- src/tradingbotsuite/v2/workers/runner.py
- tests/v2/test_validation_worker_phase32.py

## Acceptance Evidence

- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_validation_worker_phase32.py -q`
  passed: 3 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_validation_phase14.py tests/v2/test_validation_worker_phase32.py -q`
  passed: 11 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q` passed: 302 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed:
  463 passed.
- `git diff --check` passed with existing LF-to-CRLF working-copy warnings
  only.
