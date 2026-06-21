# WPR106-408 V2 Microstructure Collection Expansion And Storage Budget

Status: closed
Owner: Codex Research Agent
Created: 2026-06-21

## Objective

Implement Phase 17 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md` by
expanding the v2 collector/archive contract for fixture-backed trades, BBO, L2
snapshot, and official-file backfill preservation. Add storage growth
visibility, retention/backup policy records, and gap/reconnect evidence without
implementing live streaming, order placement, paper trading, sizing, runtime
mode changes, candidate packs, or promotion behavior.

## Audit IDs

- `V2-AUD-COLLECT-002`
- `V2-AUD-ARCH-005`

## Dependencies

- Phase 7 durable worker and collector job skeletons.
- Phase 8 archive raw-first manifest and market-data pipelines.
- Phase 16 event-driven engine skeleton microstructure fixture path.
- `docs/contracts/archive_contract.md`
- `docs/contracts/collector_job_contract.md`

## Allowed Paths

- `docs/contracts/archive_contract.md`
- `docs/contracts/collector_job_contract.md`
- `src/tradingbotsuite/v2/archive/**`
- `src/tradingbotsuite/v2/collectors/**`
- `src/tradingbotsuite/v2/workers/**`
- `tests/v2/**`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-408-v2-microstructure-collection-expansion-and-storage-budget.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Fixture and official-file archive writes are raw preservation only; they are
  not live capture proof, order readiness, or accepted backtest evidence.
- No venue network streaming, live API reads, live imports, paper/live
  artifacts, order placement, sizing, runtime-mode changes, candidate packs, or
  promotion behavior.
- Gap/reconnect evidence must be recorded instead of silent success when a job
  reports capture interruptions.
- Storage and retention reporting must be visibility/policy evidence only; no
  deletion or backup transfer is authorized in this packet.

## Acceptance Criteria

- Trades, BBO, and L2 fixture payloads are raw-preserved and manifest-recorded.
- Official S3-style local files are preserved in the raw archive with manifest
  identity.
- Gap and reconnect metadata are recorded and linked to collector job output.
- Storage growth is visible through a budget report.
- Retention/backup policy is recorded without deleting archive files.
- Event-driven engine tests consume fixture microstructure rows compatible with
  the archive collector path.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_microstructure_collection_phase17.py -q
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

- Real venue WebSocket or S3 network ingestion becomes necessary.
- A no-touch live/runtime/order/sizing path must be modified.
- Retention or backup policy implementation would delete, move, or upload
  archive files rather than record policy evidence.
- The event-driven engine requires realistic fill or queue modeling beyond the
  existing fixture-only skeleton.

## Completion Notes

Closed on 2026-06-21.

- Added microstructure archive schemas and helpers for:
  - trade, BBO, and L2 fixture rows;
  - raw JSONL.zstd capture through the existing archive manifest store;
  - official S3-style local native-file preservation;
  - microstructure quality reports;
  - storage budget reports;
  - record-only retention/backup policy evidence.
- Added durable collector worker kinds for:
  - `websocket_trade_capture`;
  - `websocket_l2_bbo_capture`;
  - `official_s3_backfill`.
- Kept the existing generic `websocket_capture` skeleton behavior unchanged.
- Wired reconnect/gap evidence to durable worker gap records for Phase 17
  fixture captures.
- Updated archive and collector contracts with the Phase 17 raw-preservation,
  storage-budget, retention-policy, and non-live constraints.
- Added `V2-AUD-ARCH-005` and `V2-AUD-COLLECT-002` to the audit index as
  `self_checked`.
- No live venue streaming, S3 network download, order placement, paper/live
  artifact, sizing instruction, runtime-mode change, candidate pack, retention
  deletion, backup transfer, or promotion behavior was implemented.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_microstructure_collection_phase17.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Result:

- Focused Phase 17 tests passed: 6 passed.
- Full v2 tests passed: 126 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- Contract-doc smoke passed: 2 passed.
- Full `compileall` for `src\tradingbotsuite` passed.
- Contract tests passed: 462 passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
