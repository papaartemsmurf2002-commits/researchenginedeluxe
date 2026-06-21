# WPR106-407 V2 Event-Driven Engine Skeleton And Microstructure Path

Status: closed
Owner: Codex Research Agent
Created: 2026-06-21

## Objective

Implement Phase 16 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`: add a
fixture-only event-driven engine interface that shares the run artifact
contract, validates a local microstructure event queue, blocks undocumented
maker assumptions, and writes research-only non-promotable artifacts.

This packet does not implement real order placement, live execution, paper
execution, sizing, runtime-mode changes, L2 archive collection, realistic queue
modeling, candidate packs, or promotion behavior.

## Audit IDs

- `V2-AUD-BTENG-002`

## Dependencies

- Phase 11 shared run artifact contract.
- Phase 12 cost model and maker-assumption guard.
- `docs/contracts/backtest_engine_contract.md`
- `docs/contracts/run_artifact_contract.md`

## Allowed Paths

- `docs/contracts/backtest_engine_contract.md`
- `docs/contracts/run_artifact_contract.md`
- `src/tradingbotsuite/v2/backtest_engine/**`
- `tests/v2/**`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-407-v2-event-driven-engine-skeleton-and-microstructure-path.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Event-driven outputs are fixture simulation artifacts, not order readiness or
  venue execution proof.
- No live venue/API reads, live imports, order placement, paper/live artifacts,
  sizing, runtime-mode changes, candidate packs, or promotion behavior.
- Maker/mixed assumptions remain blocked unless a queue model is explicitly
  documented.

## Acceptance Criteria

- Event-driven engine can run fixture panel and microstructure rows.
- Event-driven output uses the same required artifact contract as vectorized
  runs.
- Missing microstructure rows fail closed with artifacts.
- Event queue ordering is deterministic and local-only.
- Maker assumptions require queue-model documentation.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_event_driven_phase16.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

No broader non-v2 tests are required unless shared implementation files outside
the v2 shell are changed.

## Stop Conditions

- A no-touch live/runtime/order/sizing path must be modified.
- Realistic queue modeling or L2 collection becomes necessary.
- Event-driven skeleton cannot emit the shared artifact contract without
  claiming fill realism.

## Completion Notes

Closed on 2026-06-21.

- Added `run_event_driven_backtest`, a fixture-only event-driven skeleton that:
  - validates local microstructure event rows;
  - requires BBO or L2 context;
  - sorts the event queue deterministically;
  - blocks maker/mixed assumptions unless queue-model metadata is documented;
  - writes the same required artifact set as vectorized runs;
  - records `engine_lane: event_driven`;
  - preserves research-only and no-order/no-sizing/no-paper/no-live boundary
    flags.
- Kept the older `run_event_driven_placeholder` for explicit blocked
  placeholder artifact-contract tests.
- Updated the backtest-engine and run-artifact contracts.
- Added `V2-AUD-BTENG-002` to the audit index as `self_checked`.
- No realistic queue model, L2 collection, order placement, paper/live
  behavior, sizing, runtime-mode change, candidate-pack writing, or promotion
  behavior was implemented.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_event_driven_phase16.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Result:

- Focused Phase 16 tests passed: 5 passed.
- Full v2 tests passed: 120 passed.
- Contract-doc smoke passed: 2 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- Full `compileall` for `src\tradingbotsuite` passed.
- Contract tests passed: 462 passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
