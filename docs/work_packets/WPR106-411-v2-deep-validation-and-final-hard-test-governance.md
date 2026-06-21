# WPR106-411 V2 Deep Validation And Final Hard-Test Governance

Status: closed
Owner: Codex Research Agent
Created: 2026-06-21

## Objective

Implement Phase 20 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md` by
adding governance models and service helpers for serious-lead deep validation
and final hard-test slots. This packet enforces one active deep-validation lead,
max three final hard-test slots, frozen evidence requirements, pre-2024
diagnostic fallback labeling, and non-live survivor reporting.

This packet does not run expensive validation jobs, tune strategies, access
lockbox results for optimization, write candidate packs, place orders, produce
paper/live signals, emit sizing instructions, change runtime mode, or create
promotion-ready artifacts.

## Audit IDs

- `V2-AUD-FINAL-001`
- `V2-AUD-VAL-002`

## Dependencies

- Phase 14 validation base.
- Phase 15 Lead Book workflow.
- `docs/contracts/validation_contract.md`
- `docs/contracts/lead_book_contract.md`

## Allowed Paths

- `docs/contracts/validation_contract.md`
- `docs/contracts/lead_book_contract.md`
- `src/tradingbotsuite/v2/validation/**`
- `tests/v2/**`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-411-v2-deep-validation-and-final-hard-test-governance.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Final hard-test survivor reports must explicitly avoid paper/live/trade
  readiness implication.
- Lockbox access is only represented as a final-phase manifest field; it does
  not authorize post-lockbox tuning.
- Frozen strategy, params, data, universe, and cost model hashes/IDs are
  required before final hard-test slot allocation.

## Acceptance Criteria

- Only one deep validation can be active at a time.
- Deep validation manifests record a full required scorecard.
- Pre-2024 fallback is diagnostic-only and cannot substitute for modern 2024+
  evidence.
- Only three final hard-test slots can be active.
- Final hard-test slots require frozen strategy, params, data, universe, and
  cost model evidence.
- Parameter edits after lockbox access are forbidden.
- Final survivor reports carry a non-live disclaimer and reject paper/live,
  trade-readiness, sizing, order, runtime, or promotion implications.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_final_validation_phase20.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
git diff --check
```

No broader non-v2 tests are required unless shared implementation files outside
the v2 shell are changed.

## Stop Conditions

- Expensive validation execution or lockbox result analysis becomes necessary.
- A no-touch live/runtime/order/sizing path must be modified.
- The workflow cannot enforce final-slot freeze requirements without weakening
  validation or Lead Book contracts.

## Completion Notes

Closed on 2026-06-21.

- Added deep-validation and final-hard-test governance models:
  - `DeepValidationScorecard`;
  - `DeepValidationManifest`;
  - `Pre2024FallbackDiagnostic`;
  - `FinalHardTestSlot`;
  - `FinalSurvivorReport`.
- Added workflow helpers enforcing:
  - one active serious-lead deep validation;
  - full scorecard recording;
  - pre-2024 fallback as diagnostic-only;
  - max three active final hard-test slots;
  - frozen strategy/params/data/universe/cost/final-phase evidence;
  - no parameter edits after lockbox access;
  - final survivor report non-live disclaimer.
- Updated validation and Lead Book contracts.
- Marked `V2-AUD-FINAL-001` and `V2-AUD-VAL-002` as `self_checked`.
- No expensive validation execution, lockbox tuning, candidate-pack writing,
  paper/live signal, sizing instruction, order placement, runtime-mode change,
  promotion behavior, or live-runtime import was implemented.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_final_validation_phase20.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Result:

- Focused Phase 20 tests passed: 7 passed.
- Full v2 tests passed: 142 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- Contract-doc smoke passed: 2 passed.
- Full `compileall` for `src\tradingbotsuite` passed.
- Contract tests passed: 462 passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
