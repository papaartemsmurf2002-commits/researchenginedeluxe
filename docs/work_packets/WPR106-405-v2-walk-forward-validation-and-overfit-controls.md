# WPR106-405 V2 Walk-Forward Validation And Overfit Controls

Status: closed
Owner: Codex Research Agent
Created: 2026-06-21

## Objective

Implement Phase 14 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`: add
walk-forward splitting, purge/embargo support, fold stability summaries,
trial-family overfit diagnostics, sweep completeness checks, and leaderboard
visibility for trial count and fold stability.

This packet extends Phase 13 ledger reporting. It does not implement Lead Book
workflow, deep validation execution orchestration, final hard-test workflow, UI,
paper/live behavior, order placement, sizing, runtime-mode changes, candidate
packs, or promotion behavior.

## Audit IDs

- `V2-AUD-VAL-001`

## Dependencies

- Phase 13 append-only ledger.
- `docs/contracts/validation_contract.md`
- `docs/contracts/ledger_contract.md`
- `src/tradingbotsuite/v2/ledger/**`

## Allowed Paths

- `docs/contracts/validation_contract.md`
- `docs/contracts/ledger_contract.md`
- `src/tradingbotsuite/v2/validation/**`
- `src/tradingbotsuite/v2/ledger/**`
- `tests/v2/**`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-405-v2-walk-forward-validation-and-overfit-controls.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Validation diagnostics are evidence gates, not trading signals.
- Trial-family diagnostics must account for every expected trial or fail
  closed.
- Do not create Lead Book rows, final hard-test decisions, paper/live
  artifacts, sizing, orders, runtime-mode changes, candidate packs, or
  promotion behavior.

## Acceptance Criteria

- Walk-forward folds are time ordered.
- Purge/embargo gaps exclude boundary rows.
- Sweep diagnostics record every expected trial or reject incomplete logging.
- Missing sweep `experiment_id` is rejected.
- Post-lockbox parameter tuning is rejected.
- Large trial-family PBO/CSCV-style diagnostics run when enough trials/folds
  exist.
- Leaderboard output includes trial count and fold stability.
- Attractive headline performance can still carry overfit warnings.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_validation_phase14.py -q
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
- Validation diagnostics need to interpret lead approval, final hard-test,
  paper/live, candidate-pack, or promotion semantics.
- Trial-family completeness cannot be checked without changing prior ledger
  packet semantics.

## Completion Notes

Closed on 2026-06-21.

- Added Phase 14 validation schemas and helpers:
  - `WalkForwardConfig`
  - `WalkForwardFold`
  - `FoldMetric`
  - `FoldStabilitySummary`
  - `TrialResult`
  - `SweepCompletenessReport`
  - `TrialFamilyReport`
- Implemented walk-forward folds with strict time ordering and explicit
  purge/embargo gap indices.
- Implemented fold stability summaries.
- Implemented sweep completeness checks that fail closed when expected trials
  are missing or unexpected rows appear.
- Implemented trial-family best-vs-median reporting, large weak-family warning,
  and a lightweight PBO/CSCV-style diagnostic when enough trials/folds exist.
- Implemented post-lockbox parameter-tuning rejection.
- Extended ledger rows and leaderboard output with trial count, fold count,
  fold stability score, family median/gap fields, and overfit warnings.
- Updated validation and ledger contracts and marked `V2-AUD-VAL-001` as
  `self_checked`.
- No Lead Book, deep validation execution orchestration, final hard-test
  workflow, UI, paper/live behavior, order placement, sizing, runtime-mode
  change, candidate-pack writing, or promotion behavior was implemented.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_validation_phase14.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Result:

- Focused Phase 14 tests passed: 8 passed.
- Full v2 tests passed: 105 passed.
- Contract-doc smoke passed: 2 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- Full `compileall` for `src\tradingbotsuite` passed.
- Contract tests passed: 462 passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
