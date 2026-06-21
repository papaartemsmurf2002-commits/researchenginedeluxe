# WPR106-456 - V2 public diagnostic cycle spec

Status: closed
Date: 2026-06-21
Branch: main (workspace branch; stage ledger role: research/v3-experimental-engine)

## Audit IDs

- V2-AUD-AUTONOMY-009
- V2-AUD-COLLECT-010

## Scope

Add a research-only public Hyperliquid diagnostic bounded-cycle spec writer.
The generated spec must use the existing durable worker loop with
`source=public_api` universe and candle collection jobs, then coverage audit,
vectorized backtest, ledger append/export, Lead Book upsert, and generated
final audit report.

This chunk does not run venue calls, collect data during spec generation,
certify historical coverage, create accepted research evidence, or mark the
repo autonomous-ready. Public API universe/candle output remains diagnostic
until real as-of historical universe evidence, coverage, independent audits,
and authoritative validation satisfy the readiness gate.

## Allowed Paths

- docs/work_packets/WPR106-456-v2-public-diagnostic-cycle-spec.md
- docs/contracts/autonomy_loop_contract.md
- docs/audit/V2_AUDIT_INDEX.md
- docs/ACTIVE_INDEX.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- src/tradingbotsuite/v2/autonomy/cycle_public.py
- src/tradingbotsuite/v2/autonomy/__init__.py
- src/tradingbotsuite/v2/cli/main.py
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
- Any credential, lockbox, coverage-floor, date-floor, venue-account, or
  checked legacy evidence material

## Expected Tests

- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_public_cycle_phase30.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_research_cycle_phase26.py tests/v2/test_autopilot_public_cycle_phase30.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
- `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- `git diff --check`

## Planned Changes

- Add a public diagnostic cycle config/result schema and writer.
- Generate public-API universe and candle worker specs with provenance/cap
  inputs and no boundary overrides.
- Preserve the existing output-ref binding chain from universe/candles to
  coverage/backtest, backtest to ledger, and ledger to Lead Book.
- Make Lead Book rows produced by this cycle non-promotable and explicitly
  blocked by public-current-universe, public-recent-window, real historical
  coverage, independent audit, and authoritative validation gaps.
- Add CLI coverage and focused tests proving the generated public spec validates
  through the bounded autopilot planner without network calls.

## Decisions Made

- Implemented public API cycle generation as a spec-writer only. It does not
  call Hyperliquid, enqueue jobs, run workers, or certify coverage.
- Kept generated cycles `sandbox_diagnostic` and `universe_mode=current`
  because public universe refresh captures the current public universe, not
  historical as-of universe evidence.
- Required a 180-day requested window so generated specs are shaped like the
  six-month research loop, while still carrying blockers because public API
  responses may not prove accepted historical coverage for that full window.
- Reused the existing durable worker chain and output-ref bindings rather than
  adding new collector behavior.
- Made the generated Lead Book step non-promotable and preloaded with public
  current-universe, recent-window, accepted historical coverage, independent
  audit, and authoritative validation blockers.

## Changed Files

- docs/work_packets/WPR106-456-v2-public-diagnostic-cycle-spec.md
- docs/contracts/autonomy_loop_contract.md
- docs/audit/V2_AUDIT_INDEX.md
- docs/ACTIVE_INDEX.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- src/tradingbotsuite/v2/autonomy/cycle_public.py
- src/tradingbotsuite/v2/autonomy/__init__.py
- src/tradingbotsuite/v2/cli/main.py
- tests/v2/test_autopilot_public_cycle_phase30.py

## Acceptance Evidence

- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_public_cycle_phase30.py -q`
  passed: 3 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_research_cycle_phase26.py tests/v2/test_autopilot_public_cycle_phase30.py -q`
  passed: 12 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q` passed: 295 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed:
  463 passed.
- `git diff --check` passed with existing LF-to-CRLF working-copy warnings
  only.
