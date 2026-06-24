# WPR106-519 - V2 Data Venue Runbook And Operator Docs

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-047`

## Objective

Complete the `DATA-018` foundation by adding a v2 Hyperliquid data-venue
runbook for operators and future agents. The runbook explains the strict-free
source order, source registry and symbol-map prerequisites, archive layers,
coverage gates, gold panel assembly, validation commands, and requester-pays
quarantine.

This packet is documentation-only. It does not add collectors, download market
data, write archive rows, run backtests, create candidate evidence, create
candidate packs, add paper/live behavior, place orders, emit sizing
instructions, change runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-519-v2-data-venue-runbook-and-operator-docs.md`
- `docs/runbooks/v2_hyperliquid_data_venue_runbook.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`

## No-Touch Paths

- No source, test, live runtime, order-placement, sizing, runtime config,
  promotion, shadow, or candidate-pack truth-layer paths.
- No collector behavior changes.
- No archive data downloads or generated market-data artifacts.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
git diff --check
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Keep the runbook aligned with
  `docs/roadmaps/V2_HYPERLIQUID_DATA_VENUE_ROADMAP.md`.
- Keep requester-pays official Hyperliquid archives quarantined under
  strict-zero-dollar mode.
- Keep gold panels research-only and non-promotable.
- Include fail-closed handling and validation commands.

## Acceptance Criteria

- Operators can identify the source order, prerequisites, outputs, blockers,
  and validation steps for the v2 data-venue roadmap.
- The runbook explicitly preserves the research-only boundary and strict-free
  policy.
- Control docs reference the runbook and `DATA-018` audit row.

## Changed Files

- `docs/runbooks/v2_hyperliquid_data_venue_runbook.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/work_packets/WPR106-519-v2-data-venue-runbook-and-operator-docs.md`

## Validation Evidence

Focused:

```text
git diff --check: passed with expected LF-to-CRLF warnings only
```

Baseline:

```text
compile src/tradingbotsuite: passed
tests/v2: 531 passed
tests/contracts: first attempt hit Windows socketpair WinError 10055 after 462 passed; rerun 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

## Closeout Notes

- Added `docs/runbooks/v2_hyperliquid_data_venue_runbook.md`.
- The runbook covers strict-free source order, requester-pays quarantine,
  prerequisites, archive layers, data-family coverage gates, gold panels,
  fail-closed handling, validation commands, and operator stops.
- The packet is documentation-only and creates no source behavior, archive
  artifacts, accepted coverage evidence, candidate-ready claim, paper/live/
  order/sizing/runtime behavior, or promotion behavior.
