# WPR106-455 - V2 autonomous readiness audit gate

Status: closed
Date: 2026-06-21
Branch: main (workspace branch; stage ledger role: research/v3-experimental-engine)

## Audit IDs

- V2-AUD-COMPLETE-002
- V2-AUD-AUDIT-006

## Scope

Add a research-only autonomous-readiness audit gate that turns the execution
brief's final checklist into a deterministic JSON report. The gate must report
missing or failed evidence as blockers and must not certify readiness unless
all required evidence items and required operational artifacts are present,
passing, and blocker-free.

This chunk does not collect real venue data, run long autonomous jobs, mark the
repo autonomous-ready, or resolve the remaining evidence gaps. It creates the
machine-readable gate that later real-archive/backtest/validation packets must
satisfy before a manager agent can claim the objective is complete.

## Allowed Paths

- docs/work_packets/WPR106-455-v2-autonomous-readiness-audit-gate.md
- docs/contracts/autonomous_readiness_contract.md
- docs/contracts/audit_report_contract.md
- docs/audit/V2_AUDIT_INDEX.md
- docs/ACTIVE_INDEX.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- src/tradingbotsuite/v2/audit/readiness.py
- src/tradingbotsuite/v2/audit/__init__.py
- src/tradingbotsuite/v2/cli/main.py
- tests/v2/test_autonomous_readiness_audit_phase29.py

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

- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autonomous_readiness_audit_phase29.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_fixture_cycle_phase28.py tests/v2/test_autonomous_readiness_audit_phase29.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
- `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- `git diff --check`

## Planned Changes

- Add an autonomous-readiness evidence schema with fixed required checklist
  keys derived from the execution brief.
- Add a readiness report writer that blocks on missing checklist items, failed
  checks, missing evidence refs, missing evidence paths, open P0/P1 counts,
  non-passing cycle execution reports, non-passing final audit reports, empty
  ledgers, and empty Lead Book files.
- Add a CLI command that consumes a readiness evidence JSON file and writes the
  deterministic readiness blocker report.
- Document that the gate is research-only and does not create candidate,
  paper/live, order, sizing, runtime, or promotion claims.
- Add tests proving incomplete current-style evidence blocks and synthetic
  complete evidence can pass only when all required artifacts are blocker-free.

## Decisions Made

- Implemented the autonomous readiness gate as a separate manager-level audit
  report instead of changing durable `AuditBlockerReport`; final audit reports
  remain non-certifying and keep `accepted_research_ready=false`.
- Required the gate to fail closed on missing checklist keys, unexpected keys,
  failed evidence items, missing evidence refs, missing evidence paths, open
  P0/P1 counts, incomplete cycle execution, non-passing final audit reports,
  empty canonical ledgers, and empty Lead Book files.
- Kept the pass path available only for complete supplied evidence so tests can
  prove semantics, while documenting that synthetic fixtures do not support a
  real manager completion claim.
- Rejected secret-like and non-JSON readiness report output paths before
  writes, matching durable audit report hygiene.

## Changed Files

- docs/work_packets/WPR106-455-v2-autonomous-readiness-audit-gate.md
- docs/contracts/autonomous_readiness_contract.md
- docs/contracts/audit_report_contract.md
- docs/audit/V2_AUDIT_INDEX.md
- docs/ACTIVE_INDEX.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- src/tradingbotsuite/v2/audit/readiness.py
- src/tradingbotsuite/v2/audit/__init__.py
- src/tradingbotsuite/v2/cli/main.py
- tests/v2/test_autonomous_readiness_audit_phase29.py

## Acceptance Evidence

- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autonomous_readiness_audit_phase29.py -q`
  passed: 5 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_fixture_cycle_phase28.py tests/v2/test_autonomous_readiness_audit_phase29.py -q`
  passed: 7 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q` passed: 292 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed:
  463 passed.
- `git diff --check` passed with existing LF-to-CRLF working-copy warnings
  only.
