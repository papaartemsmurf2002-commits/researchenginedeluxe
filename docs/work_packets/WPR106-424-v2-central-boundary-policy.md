# WPR106-424 V2 Central Boundary Policy

Status: self_checked
Owner: Codex Manager Development Agent
Created: 2026-06-21

## Objective

Close the audit hole that v2 boundary flags are validated by repeated local
convention. Add a central research-boundary policy and migrate the highest-risk
v2 artifacts to validate their canonical flags through that policy.

This packet does not change any artifact from research-only to accepted,
candidate, paper, live, sizing, runtime, order, or promotion status.

## Audit IDs

- `V2-AUD-SEC-005`
- `V2-AUD-AUTONOMY-003`
- `V2-AUD-BTENG-005`
- `V2-AUD-BTDATA-003`
- `V2-AUD-LEDGER-003`
- `V2-AUD-LEAD-003`
- `V2-AUD-STRAT-005`

## Allowed Paths

- `docs/work_packets/WPR106-424-v2-central-boundary-policy.md`
- `docs/contracts/security_boundary_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `src/tradingbotsuite/v2/security/boundary.py`
- `src/tradingbotsuite/v2/security/__init__.py`
- `src/tradingbotsuite/v2/autonomy/schemas.py`
- `src/tradingbotsuite/v2/backtest_engine/artifacts.py`
- `src/tradingbotsuite/v2/backtest_data/schemas.py`
- `src/tradingbotsuite/v2/ledger/schemas.py`
- `src/tradingbotsuite/v2/ledger/service.py`
- `src/tradingbotsuite/v2/lead_book/schemas.py`
- `src/tradingbotsuite/v2/strategy_specs/schemas.py`
- `tests/v2/test_boundary_policy_phase24.py`
- `tests/v2/test_autonomy_phase23.py`
- `tests/v2/test_backtest_engine_phase11.py`
- `tests/v2/test_backtest_data_phase9.py`
- `tests/v2/test_ledger_phase13.py`
- `tests/v2/test_lead_book_phase15.py`
- `tests/v2/test_strategy_specs_phase10.py`

## No-Touch Paths

- `src/**/live/**`
- `src/**/runtime.py`
- `run_live_smoke.py`
- `run_manual.py`
- order-placement adapters, broker helpers, exchange submit helpers
- sizing/runtime configuration paths
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `src/tradingbotsuite/promotion/**`
- `src/tradingbotsuite/live/shadow_loader.py`
- committed generated research evidence under `data/research/**`
- legacy GUI/web/operator source paths
- `src/tradingbot/**`
- `.env`, credential files, local SQLite operator DBs, private caches

## Boundary Constraints

- No no-touch path may be edited.
- The central policy must derive expected flags from the canonical v2 boundary
  defaults.
- Migrated artifacts must fail closed when any required boundary field is
  missing or set to a non-canonical value.
- Error messages may be normalized to the central policy wording, but behavior
  must not become weaker.
- This packet may not create or rewrite generated research evidence.

## Expected Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_boundary_policy_phase24.py tests\v2\test_autonomy_phase23.py tests\v2\test_backtest_engine_phase11.py tests\v2\test_backtest_data_phase9.py tests\v2\test_ledger_phase13.py tests\v2\test_lead_book_phase15.py tests\v2\test_strategy_specs_phase10.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Acceptance Criteria

- A central boundary helper exposes canonical true/false field sets and a
  reusable `require_research_boundary` validator.
- The policy rejects missing canonical fields and wrong values with explicit
  reasons.
- Autonomy manifests/steps, run manifests/metrics/contexts, backtest-data
  requests/manifests, ledger rows, Lead Book rows, strategy specs, signal rows,
  and signal frames use the central validator.
- Focused tests prove the central policy and at least one migrated artifact per
  migrated bounded context fail closed on forbidden flags.
- Control docs record the packet and no autonomous-ready, accepted-evidence,
  paper/live/order/sizing/runtime/promotion claim is created.

## Completion Notes

Implemented and self-checked on 2026-06-21.

Changed files stayed inside the declared packet scope after the scope was
expanded to include `src/tradingbotsuite/v2/ledger/service.py`, which is
required to persist the complete canonical boundary invariant in ledger rows.

Changed files:

- `docs/work_packets/WPR106-424-v2-central-boundary-policy.md`
- `docs/contracts/security_boundary_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `src/tradingbotsuite/v2/security/boundary.py`
- `src/tradingbotsuite/v2/security/__init__.py`
- `src/tradingbotsuite/v2/autonomy/schemas.py`
- `src/tradingbotsuite/v2/backtest_engine/artifacts.py`
- `src/tradingbotsuite/v2/backtest_data/schemas.py`
- `src/tradingbotsuite/v2/ledger/schemas.py`
- `src/tradingbotsuite/v2/ledger/service.py`
- `src/tradingbotsuite/v2/lead_book/schemas.py`
- `src/tradingbotsuite/v2/strategy_specs/schemas.py`
- `tests/v2/test_boundary_policy_phase24.py`
- `tests/v2/test_strategy_specs_phase10.py`

Decisions made:

- The central policy lives under `tradingbotsuite.v2.security.boundary` because
  the invariant is a security/product-boundary concern.
- The policy derives canonical field names and expected values from
  `RESEARCH_BOUNDARY`.
- Migrated artifacts require all canonical fields to be present and canonical.
- Backtest metrics and strategy contexts now carry the full canonical invariant
  rather than only the three basic flags.
- Ledger rows now include and persist `candidate_pack_eligible=false` and
  `runtime_mode_change=false`.
- Existing local error messages were normalized to central-policy reasons such
  as `live_signal_must_be_false`.

Acceptance evidence:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_boundary_policy_phase24.py tests\v2\test_autonomy_phase23.py tests\v2\test_backtest_engine_phase11.py tests\v2\test_backtest_data_phase9.py tests\v2\test_ledger_phase13.py tests\v2\test_lead_book_phase15.py tests\v2\test_strategy_specs_phase10.py -q
# 58 passed

$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
# 185 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 463 passed

git diff --check
# passed with existing LF-to-CRLF warnings only
```

No accepted-evidence artifact, autonomous-ready claim, candidate-ready claim,
paper/live signal, order-placement behavior, sizing instruction, runtime-mode
change, committed generated research evidence, or promotion-ready artifact was
created.
