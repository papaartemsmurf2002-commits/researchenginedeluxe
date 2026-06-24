# WPR106-515 - V2 Data-Family Coverage Gate Foundation

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-043`

## Objective

Start `DATA-016` by adding a research-only data-family coverage gate
foundation. The helper consumes existing `DataFamilyCoverageReport` objects,
requires an explicit family set for a symbol/window context, and returns a
deterministic pass/block result with missing and rejected family evidence.

This packet does not add collectors, download market data, write archive rows,
create gold panels, run backtests, create candidate evidence, create candidate
packs, add paper/live behavior, place orders, emit sizing instructions, change
runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-515-v2-data-family-coverage-gate-foundation.md`
- `src/tradingbotsuite/v2/data_sources/coverage_gates.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_family_coverage_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_data_family_coverage_gate_phase69.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No collector behavior changes in this packet.
- No archive data downloads, generated market-data rows, accepted historical
  coverage proof creation, data mutation, or gold panel writes.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_data_family_coverage_gate_phase69.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Reuse existing `DataFamilyCoverageReport` acceptance semantics.
- Gate results must be deterministic, research-only, observe-only, and
  non-promotable.
- Treat missing required families, non-accepted required family reports,
  mismatched symbol/ref context, empty required family sets, and empty report
  inputs as fail-closed blockers.
- The gate result is not itself a gold panel and does not create accepted
  coverage evidence.

## Acceptance Criteria

- Required family coverage passes only when every required family has an
  accepted coverage report meeting the requested minimum.
- Missing families and rejected families are explicit result fields and blocker
  reasons.
- Mismatched symbol/ref context fails closed.
- Gate results remain research-only, observe-only, non-promotable, and not
  candidate or promotion evidence.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/coverage_gates.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `tests/v2/test_data_family_coverage_gate_phase69.py`
- `docs/contracts/data_family_coverage_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/work_packets/WPR106-515-v2-data-family-coverage-gate-foundation.md`

## Validation Evidence

Focused:

```text
tests/v2/test_data_family_coverage_gate_phase69.py: 7 passed
```

Baseline:

```text
compile src/tradingbotsuite: passed
tests/v2: 510 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

## Closeout Notes

- Added deterministic `DataFamilyCoverageGateResult` and
  `evaluate_data_family_coverage_gate()` over existing
  `DataFamilyCoverageReport` objects.
- Required families pass only when already accepted coverage reports meet the
  requested coverage minimum and carry no blocker reasons.
- Empty inputs, missing required families, rejected family reports, mismatched
  symbol/ref context, and empty required-family sets fail closed.
- Gate results do not create accepted coverage evidence, gold panels,
  candidate-ready claims, paper/live/order/sizing/runtime, or promotion
  behavior.
