# WPR106-406 V2 Lead Book And Lead Workflow

Status: closed
Owner: Codex Research Agent
Created: 2026-06-21

## Objective

Implement Phase 15 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`: add
the non-promotable Lead Book schema, Parquet/CSV store, lead creation from
artifacts, human inspection and agent approval workflow, ROI assumption fields,
lead promotion gate checks, diminishing-returns warning, and pre-2024 fallback
metadata handling.

This packet does not implement deep validation execution, final hard-test
workflow, UI, paper/live behavior, order placement, sizing, runtime-mode
changes, candidate packs, or promotion behavior.

## Audit IDs

- `V2-AUD-LEAD-001`

## Dependencies

- Phase 13 append-only ledger.
- Phase 14 validation diagnostics.
- `docs/contracts/lead_book_contract.md`

## Allowed Paths

- `docs/contracts/lead_book_contract.md`
- `src/tradingbotsuite/v2/lead_book/**`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/**`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-406-v2-lead-book-and-lead-workflow.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Lead rows are not candidates and cannot imply paper/live/trade readiness.
- ROI projections are assumptions only and must be explicitly marked as not
  claims.
- Deep validation requests require human inspection completion and agent
  approval after inspection.
- Do not create final hard-test decisions, paper/live artifacts, sizing,
  orders, runtime-mode changes, candidate packs, or promotion behavior.

## Acceptance Criteria

- Agents can create lead rows with source artifact hashes.
- Lead rows require observed and projected ROI fields.
- ROI projection is marked as assumption/not claim.
- Human inspection and agent approval gates block deep validation starts.
- Lead gates enforce six-losing-month failure, trade-frequency minimum, and
  profit-concentration warning/failure thresholds.
- Diminishing returns warnings are recorded.
- Missing pre-2024 fallback metadata marks a lead failed/blocked.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_lead_book_phase15.py -q
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
- Lead workflow requires final hard-test, candidate-pack, paper/live, or
  promotion semantics.
- Human inspection/agent approval gating cannot remain explicit in schema and
  store transitions.

## Completion Notes

Closed on 2026-06-21.

- Added Phase 15 Lead Book schemas:
  - `LeadBookRow`
  - `LeadState`
  - `LeadGateResult`
  - human inspection and agent approval enums
  - trade, monthly stability, and PnL concentration summaries
- Added `create_lead_from_source` with source artifact SHA-256 hashing.
- Added `LeadBookStore` canonical Parquet storage and generated CSV export.
- Added workflow transitions for human inspection request/completion, agent
  approval after inspection, and deep-validation request gating.
- Added lead gate checks for:
  - minimum five average trades per month;
  - minimum six usable months;
  - six losing months in a year;
  - top-two-trade and best-month profit concentration warning/failure
    thresholds;
  - diminishing returns warnings;
  - missing pre-2024 fallback metadata.
- Added `redx lead create`, `redx lead list`, `redx lead inspect-request`, and
  `redx lead approve-after-human-inspection`.
- Updated the Lead Book contract and marked `V2-AUD-LEAD-001` as
  `self_checked`.
- No deep validation execution, final hard-test workflow, UI, paper/live
  behavior, order placement, sizing, runtime-mode change, candidate-pack
  writing, or promotion behavior was implemented.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_lead_book_phase15.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Result:

- Focused Phase 15 tests passed: 10 passed.
- Full v2 tests passed: 115 passed.
- Contract-doc smoke passed: 2 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- Full `compileall` for `src\tradingbotsuite` passed.
- Contract tests passed: 462 passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
