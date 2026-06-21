# WPR106-457 - V2 strategy queue scan

Status: closed
Date: 2026-06-21
Branch: main (workspace branch; stage ledger role: research/v3-experimental-engine)

## Audit IDs

- V2-AUD-AUTONOMY-010
- V2-AUD-STRAT-006

## Scope

Add a research-only local strategy-spec queue scanner for the autonomous loop.
The scanner must discover declarative JSON/YAML strategy specs from a bounded
local directory, validate each spec through the existing v2 strategy-spec
validator, write normalized copies for valid specs, and produce a deterministic
queue manifest that records accepted and rejected specs with blockers.

This chunk does not enqueue worker jobs, run backtests, collect venue data,
certify historical coverage, create accepted research evidence, or mark the
repo autonomous-ready. The queue manifest is input hygiene and blocker evidence
only.

## Allowed Paths

- docs/work_packets/WPR106-457-v2-strategy-queue-scan.md
- docs/contracts/autonomy_loop_contract.md
- docs/contracts/strategy_spec_contract.md
- docs/audit/V2_AUDIT_INDEX.md
- docs/ACTIVE_INDEX.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- src/tradingbotsuite/v2/autonomy/strategy_queue.py
- src/tradingbotsuite/v2/autonomy/__init__.py
- src/tradingbotsuite/v2/cli/main.py
- tests/v2/test_autopilot_strategy_queue_phase31.py

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

- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_strategy_queue_phase31.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_strategy_specs_phase10.py tests/v2/test_autopilot_strategy_queue_phase31.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
- `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- `git diff --check`

## Planned Changes

- Add strategy-queue config, manifest, item, and result schemas with full v2
  research-only boundary flags.
- Scan only local `.json`, `.yaml`, and `.yml` declarative strategy spec files;
  reject unsupported and secret-like paths without executing or importing them.
- Validate accepted specs through the existing declarative strategy validator
  and write normalized JSON copies under the requested output root.
- Add an autopilot CLI command that writes the manifest and prints counts,
  blockers, and non-readiness boundary fields.
- Update autonomy and strategy-spec contracts to define the scanner as an
  input-hygiene step, not execution evidence.
- Add focused tests for accepted, invalid, unsupported, secret-like, and CLI
  scanner behavior.

## Decisions Made

- Implemented the queue scanner as an `autopilot` input-hygiene command rather
  than a worker or scheduler action. It writes manifests and normalized specs
  only; it does not enqueue or run research-cycle jobs.
- Kept queue manifests `input_hygiene_only` with
  `accepted_research_ready=false` and the full canonical research-only
  boundary invariant.
- Rejected unsupported file suffixes and secret-like filenames before reading
  or hashing their contents. Supported JSON/YAML files are still parsed only
  through the existing strategy-spec loader and validator.
- Rejected output roots inside the strategy root to avoid rescanning generated
  normalized specs on repeated runs.
- Made the manifest ID deterministic from the normalized manifest payload
  excluding the ID field.

## Changed Files

- docs/work_packets/WPR106-457-v2-strategy-queue-scan.md
- docs/contracts/autonomy_loop_contract.md
- docs/contracts/strategy_spec_contract.md
- docs/audit/V2_AUDIT_INDEX.md
- docs/ACTIVE_INDEX.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- src/tradingbotsuite/v2/autonomy/strategy_queue.py
- src/tradingbotsuite/v2/autonomy/__init__.py
- src/tradingbotsuite/v2/cli/main.py
- tests/v2/test_autopilot_strategy_queue_phase31.py

## Acceptance Evidence

- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_strategy_queue_phase31.py -q`
  passed: 4 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_strategy_specs_phase10.py tests/v2/test_autopilot_strategy_queue_phase31.py -q`
  passed: 16 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q` passed: 299 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed:
  463 passed.
- `git diff --check` passed with existing LF-to-CRLF working-copy warnings
  only.
