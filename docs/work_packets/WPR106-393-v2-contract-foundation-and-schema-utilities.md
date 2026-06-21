# WPR106-393 V2 Contract Foundation And Schema Utilities

Status: closed
Owner: Codex Research Agent
Created: 2026-06-20

## Objective

Implement Phase 2 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`: create
the schema-first v2 contract foundation before business logic grows, and add
minimal Python schema, hashing, UTC time, and path-policy utilities required by
the roadmap.

This packet is contract/schema foundation work only. It does not implement real
archive writing, universe refresh, venue collection, data-quality scanning,
backtest execution, strategy evaluation, ledger appends, Lead Book storage,
worker execution, paper/live behavior, sizing, order placement, candidate-pack
writing, or promotion.

## Audit IDs

- `V2-AUD-CONTRACTS-001`
- `V2-AUD-SCOPE-003`
- `V2-AUD-ARCH-001`
- `V2-AUD-SEC-002`

## Dependencies

- `docs/PRODUCT_SCOPE.md`
- `docs/V2_DECISION_REGISTER.md`
- `docs/V2_NO_TOUCH_PATHS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-391-v2-phase0-scope-source-lock-and-safety-rails.md`
- `docs/work_packets/WPR106-392-v2-package-skeleton-config-and-import-guard.md`
- `src/tradingbotsuite/v2/**`
- `tests/v2/**`

## Allowed Paths

- `docs/V2_LEGACY_CLASSIFICATION.md`
- `docs/contracts/archive_contract.md`
- `docs/contracts/universe_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/data_quality_contract.md`
- `docs/contracts/backtest_data_service_contract.md`
- `docs/contracts/strategy_spec_contract.md`
- `docs/contracts/strategy_plugin_contract.md`
- `docs/contracts/backtest_engine_contract.md`
- `docs/contracts/cost_model_contract.md`
- `docs/contracts/run_artifact_contract.md`
- `docs/contracts/ledger_contract.md`
- `docs/contracts/lead_book_contract.md`
- `docs/contracts/validation_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/contracts/security_boundary_contract.md`
- `src/tradingbotsuite/v2/archive/**`
- `src/tradingbotsuite/v2/backtest_engine/**`
- `src/tradingbotsuite/v2/config/**`
- `src/tradingbotsuite/v2/costs/**`
- `src/tradingbotsuite/v2/lead_book/**`
- `src/tradingbotsuite/v2/ledger/**`
- `src/tradingbotsuite/v2/security/**`
- `src/tradingbotsuite/v2/universe/**`
- `src/tradingbotsuite/v2/validation/**`
- `tests/v2/**`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-393-v2-contract-foundation-and-schema-utilities.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Do not create or modify candidate packs.
- Do not create paper/live artifacts.
- Do not place orders, change runtime mode, write live configuration, or add
  sizing/order-placement behavior.
- Do not touch no-touch paths outside the explicitly allowed v2 shell/docs.
- Utilities must be deterministic and fail closed on unsafe paths or boundary
  metadata.

## Acceptance Criteria

- Section 7 contract files exist.
- Contract docs name the initial schema classes they govern.
- Initial schema models exist for archive config, universe config, validation
  config, lockbox policy, cost model config, run manifest skeleton, ledger row
  skeleton, and Lead Book row skeleton.
- Hash utilities provide stable canonical JSON, file SHA-256, and sorted
  manifest-row hashing.
- UTC timestamp utilities exist.
- Path policy rejects traversal outside archive/run roots.
- Focused v2 contract/schema tests pass.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
git diff --check
```

No full contracts run is required unless this packet touches shared non-v2
implementation files, which it explicitly does not.

## Stop Conditions

- A no-touch live/runtime/order/sizing path must be modified.
- A real collector, backtest, archive writer, ledger append, Lead Book store,
  candidate-pack, paper/live, order, sizing, runtime, or promotion behavior
  becomes necessary.

## Completion Notes

Closed on 2026-06-20.

- Added Section 7 v2 contract documents for archive, universe, venue adapter,
  collector jobs, data quality, backtest data service, strategy specs, strategy
  plugins, backtest engine, cost model, run artifacts, ledger, Lead Book,
  validation, worker jobs, and security boundary.
- Added `docs/V2_LEGACY_CLASSIFICATION.md`.
- Added initial schema skeletons:
  - `ArchiveConfig`, `ArchiveLayer`, `ArchiveSnapshotRef`
  - `UniverseConfig`, `UniverseMode`, `UniverseSnapshotRef`
  - `ValidationConfig`, `LockboxPolicy`
  - `CostModelConfig`
  - `RunManifest`
  - `LedgerRow`
  - `LeadBookRow`, `LeadState`
  - `PathPolicy`
- Added deterministic utilities:
  - canonical JSON bytes/hash
  - file SHA-256
  - sorted manifest-row hash
  - UTC timestamp normalization/formatting
  - root containment path policy
- Added focused tests for the Phase 2 acceptance criteria in
  `tests/v2/test_contract_foundation.py` and
  `tests/v2/test_contract_docs.py`.
- Marked `V2-AUD-CONTRACTS-001`, `V2-AUD-SCOPE-003`,
  `V2-AUD-ARCH-001`, and `V2-AUD-SEC-002` as `self_checked`.
- Left later archive implementation as planned under `V2-AUD-ARCH-002`.
- No real archive writer, collector, universe refresh, data-quality scanner,
  strategy evaluator, backtest runner, ledger append, Lead Book store, worker,
  paper/live, order, sizing, runtime, candidate-pack, or promotion behavior was
  implemented.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
git diff --check
```

Result:

- Focused v2 tests passed: 15 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
