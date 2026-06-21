# WPR106-395 V2 Archive Layout Raw Writer Manifests And Snapshots

Status: closed
Owner: Codex Research Agent
Created: 2026-06-20

## Objective

Implement Phase 4 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`: build
the v2 archive storage foundation before large collection. This includes
deterministic archive paths, safe archive initialization, JSONL.zst raw writes,
Parquet bronze/silver/gold table writes, manifest records, ingestion run
records, archive validation, deterministic snapshots, and focused fixture
tests.

This packet implements archive infrastructure only. It does not implement
Hyperliquid collection, universe refresh, strategy evaluation, backtest
execution, ledger append workflow, Lead Book storage, UI replacement,
paper/live behavior, sizing, order placement, candidate-pack writing, or
promotion.

## Audit IDs

- `V2-AUD-ARCH-002`
- `V2-AUD-ARCH-003`

## Dependencies

- `docs/contracts/archive_contract.md`
- `docs/contracts/security_boundary_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-393-v2-contract-foundation-and-schema-utilities.md`
- `src/tradingbotsuite/v2/archive/hashing.py`
- `src/tradingbotsuite/v2/archive/schemas.py`
- `src/tradingbotsuite/v2/security/path_policy.py`

## Allowed Paths

- `docs/contracts/archive_contract.md`
- `src/tradingbotsuite/v2/archive/**`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/**`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-395-v2-archive-layout-raw-writer-manifests-and-snapshots.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Do not create or modify candidate packs.
- Do not create paper/live artifacts.
- Do not place orders, change runtime mode, write live configuration, or add
  sizing/order-placement behavior.
- Archive writes are limited to explicitly supplied archive roots.
- Raw writes must fail rather than overwrite existing files.
- CLI archive commands must operate on local files only and must not fetch venue
  data.

## Acceptance Criteria

- `python -m tradingbotsuite.v2.cli.main archive init --archive-root <dir>`
  creates the directory tree safely.
- Raw payloads are written before normalization as `.jsonl.zst`.
- File manifests record SHA-256, byte size, row count, layer, schema version,
  and source parent IDs.
- Ingestion run records are written.
- Snapshot ID changes when included input changes.
- Bronze/silver fixture rebuild is deterministic.
- Archive validation detects a missing manifest file.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
git diff --check
```

No broad non-v2 tests are required unless shared implementation files outside
the v2 shell are changed.

## Stop Conditions

- A no-touch live/runtime/order/sizing path must be modified.
- A real venue collector, universe refresh, strategy evaluator, backtest
  runner, ledger workflow, Lead Book store, candidate-pack, paper/live, order,
  sizing, runtime, or promotion behavior becomes necessary.

## Completion Notes

Closed on 2026-06-20.

- Added deterministic archive layout/path policy in
  `src/tradingbotsuite/v2/archive/layout.py`.
- Added `ArchiveManifestStore` with Parquet-backed `file_manifest`,
  `ingestion_runs`, and `archive_snapshots` tables.
- Added `RawJsonlZstdWriter` using PyArrow's ZSTD codec, with raw append-only
  write behavior and manifest/ingestion-run registration.
- Added deterministic Parquet writer for bronze, silver, and gold layer tables.
- Added archive snapshot builder with deterministic snapshot IDs over included
  file manifest identity, excluding write-time metadata.
- Added `archive init`, `archive validate`, and `archive snapshot` commands to
  the v2 CLI shell. These commands operate on local archive roots only and do
  not fetch venue data.
- Extended archive contract schema names for the new implementation records.
- Added focused Phase 4 tests under `tests/v2/archive/`.
- Marked `V2-AUD-ARCH-002` and `V2-AUD-ARCH-003` as `self_checked`.
- No Hyperliquid collection, universe refresh, strategy evaluation, backtest
  execution, ledger append workflow, Lead Book storage, UI replacement,
  paper/live behavior, sizing, order placement, candidate-pack writing, or
  promotion behavior was implemented.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
git diff --check
```

Result:

- Focused v2 tests passed: 27 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
