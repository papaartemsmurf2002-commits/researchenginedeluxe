# WPR106-471 - V2 Ledger Validation Manifest Authority

Status: self_checked
Audit ID: `V2-AUD-LEDGER-005`
Related audit IDs: `V2-AUD-VAL-003`, `V2-AUD-AUTONOMY-011`,
`V2-AUD-AUTONOMY-015`

## Objective

Make the append-only ledger preserve the durable validation gate result when a
`validation_manifest_path` is supplied. WPR106-469 proved that the public
diagnostic cycle can run through validation and ledger, but the ledger row used
the pre-validation `run_manifest.validation_status=pass` while the validation
gate manifest correctly reported `validation_status=fail` with
`cost_dependent_failure`.

The ledger must log pass/fail trial outcomes honestly. A completed backtest may
remain `row_status=succeeded`, but its ledger `validation_status`,
`walk_forward_pass`, and `blocker_reasons` must reflect the post-backtest
validation gate when that manifest is bound into the ledger job.

## Allowed Paths

- `docs/work_packets/WPR106-471-v2-ledger-validation-manifest-authority.md`
- `src/tradingbotsuite/v2/ledger/schemas.py`
- `src/tradingbotsuite/v2/ledger/service.py`
- `src/tradingbotsuite/v2/ledger/jobs.py`
- `tests/v2/test_ledger_phase13.py`
- `tests/v2/test_workers_phase7.py`
- `docs/contracts/ledger_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## No-Touch Paths

- `src/**/live/**`
- `src/**/runtime.py`
- `run_live_smoke.py`
- `run_manual.py`
- order-placement, broker, exchange-submit, sizing, runtime-config, promotion,
  shadow, and candidate-pack truth-layer paths
- committed `data/research/fixtures/**`
- committed `data/research/historical_cycles/**`
- legacy GUI/operator UI paths
- `src/tradingbot/**`
- `.env`, credential files, local SQLite operator DBs, private caches, and
  unreviewed generated `outputs/**`

## Expected Commands

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_ledger_phase13.py tests/v2/test_workers_phase7.py -q
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_public_cycle_phase30.py tests/v2/test_autopilot_research_cycle_runner_phase27.py -q
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
git diff --check
```

After the fix, rerun a fresh WPR106-469 public diagnostic cycle and confirm the
ledger row records `validation_status=fail` and the validation blocker.

## Planned Changed Files

- `docs/work_packets/WPR106-471-v2-ledger-validation-manifest-authority.md`
- `src/tradingbotsuite/v2/ledger/schemas.py`
- `src/tradingbotsuite/v2/ledger/service.py`
- `src/tradingbotsuite/v2/ledger/jobs.py`
- `tests/v2/test_ledger_phase13.py`
- `tests/v2/test_workers_phase7.py`
- `docs/contracts/ledger_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Changed Files

- `docs/work_packets/WPR106-471-v2-ledger-validation-manifest-authority.md`
- `src/tradingbotsuite/v2/ledger/schemas.py`
- `src/tradingbotsuite/v2/ledger/service.py`
- `src/tradingbotsuite/v2/ledger/jobs.py`
- `tests/v2/test_ledger_phase13.py`
- `tests/v2/test_workers_phase7.py`
- `docs/contracts/ledger_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Decisions Made

- The ledger remains append-only and still appends completed backtests even when
  validation fails; failed validation is represented in
  `validation_status=fail` and blocker reasons rather than by hiding the row.
- `validation_manifest_path` is optional for backward compatibility with
  existing direct append tests and older run manifests. When supplied, it must
  match the run ID and run-manifest SHA-256 before it can override ledger
  validation fields.
- This packet does not alter coverage floors, lockbox policy, date floors,
  candidate language, or promotion behavior.

## Acceptance Evidence

- WPR106-469 rerun after WPR106-470 proved the failure condition: validation
  gate manifest reported `validation_status=fail` with
  `cost_dependent_failure`, while the ledger row still preserved the pre-gate
  run-manifest `validation_status=pass`.
- `LedgerAppendRequest` now accepts optional `validation_manifest_path`.
  `append_run_to_ledger` validates the supplied manifest schema, run ID,
  run-manifest SHA-256, pass/fail blocker consistency, and research boundary
  flags before using it as ledger validation authority.
- `ledger_row_from_manifest` now uses the bound validation manifest, when
  supplied, for `validation_status`, `walk_forward_pass`, blocker reasons,
  fold summary fields, `cost_fragile_warning`, and
  `validation_manifest_path`.
- The durable `ledger_append_export` worker now accepts
  `validation_manifest_path`, requires it to be an existing `.json` file when
  provided, passes it to the ledger service, and surfaces the resulting
  validation status and blockers through worker output refs.
- `docs/contracts/ledger_contract.md` now records that supplied validation gate
  manifests become authoritative only after schema, run-ID, run-manifest
  SHA-256, blocker-consistency, and boundary checks pass.
- Direct ledger regressions added:
  `test_ledger_append_uses_validation_gate_manifest_when_provided` and
  `test_ledger_append_rejects_validation_gate_manifest_for_different_run`.
- Worker regression added:
  `test_ledger_append_export_worker_uses_bound_validation_manifest`.
- Focused validation passed:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_ledger_phase13.py tests/v2/test_workers_phase7.py -q`
  (64 passed).
- Final WPR106-469 rerun after this fix wrote validation gate manifest SHA-256
  `45e8b6bb392ddbc800616f34d69c066acafa52d5d4e81590683195047ec6ba16` with
  `validation_status=fail` and `blocker_reasons=['cost_dependent_failure']`.
  The generated ledger row now records `validation_status=fail`,
  `walk_forward_pass=false`, `cost_fragile_warning=true`, and blockers
  `validation_status_fail,cost_dependent_failure`.
- The final audit report includes `validation_status_fail` in blocker evidence
  and remains `completed_with_blockers`, `accepted_research_ready=false`, and
  `promotion_ready=false`.
- Broader autonomy validation passed:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_autopilot_public_cycle_phase30.py tests/v2/test_autopilot_research_cycle_runner_phase27.py -q`
  (11 passed).
- Final validation passed: `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  (328 passed), `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  (463 passed), `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite`
  (passed), and `git diff --check` (passed with expected LF-to-CRLF warnings).
