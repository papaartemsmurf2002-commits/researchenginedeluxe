# WPR106-404 V2 Append-Only Ledger And Generated Exports

Status: closed
Owner: Codex Research Agent
Created: 2026-06-21

## Objective

Implement Phase 13 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`: add
the v2 append-only canonical experiment ledger, generated CSV/XLSX exports,
duplicate detection, failed-trial logging, and a conservative leaderboard
report.

This packet consumes Phase 11/12 run manifests and artifacts. It does not add
Lead Book workflow, validation walk-forward engines, UI, paper/live behavior,
order placement, sizing, runtime-mode changes, candidate packs, or promotion
behavior.

## Audit IDs

- `V2-AUD-LEDGER-001`

## Dependencies

- Phase 11 run artifact contract.
- Phase 12 cost manifest and stress matrix contract.
- `docs/contracts/ledger_contract.md`
- `src/tradingbotsuite/v2/backtest_engine/**`
- `src/tradingbotsuite/v2/costs/**`

## Allowed Paths

- `docs/contracts/ledger_contract.md`
- `src/tradingbotsuite/v2/ledger/**`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/**`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-404-v2-append-only-ledger-and-generated-exports.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- The canonical ledger is Parquet; CSV/XLSX are generated views only.
- Manual spreadsheet edits must never become canonical ledger truth.
- Failed and blocked trials remain loggable and countable.
- Duplicate `run_id` append attempts fail closed.
- Do not create Lead Book rows, candidate packs, paper/live artifacts, sizing,
  orders, runtime-mode changes, or promotion behavior.

## Acceptance Criteria

- Valid succeeded and failed run manifests append one row each.
- Invalid or incomplete manifests cannot enter the canonical ledger.
- Duplicate `run_id` is rejected.
- CSV and XLSX exports are generated from the canonical Parquet ledger.
- Manual spreadsheet edits are ignored by canonical reads and regenerated away.
- Leaderboard excludes sandbox/current-universe evidence claims and ranks net
  costed performance rather than gross-only performance.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_ledger_phase13.py -q
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
- Leaderboard ranking requires Lead Book, final validation, paper/live, or
  promotion semantics.
- Append-only behavior cannot be enforced without a separate integrity packet.
- Generated spreadsheet output becomes a source of truth.

## Completion Notes

Closed on 2026-06-21.

- Added Phase 13 ledger schemas:
  - `LedgerRow`
  - `LedgerAppendRequest`
  - `LeaderboardRow`
- Added append-only ledger service behavior:
  - parse and validate `run_manifest.json`;
  - reject missing manifests, missing validation status, invalid manifests,
    duplicate `run_id`, gross-only metrics, boundary violations, accepted
    current-universe claims, accepted pre-2024 starts, accepted short usable
    windows, and accepted lockbox overlap;
  - log succeeded and failed/blocked trials;
  - write canonical Parquet rows with deterministic `ledger_index` and
    `row_hash`;
  - reject canonical reads when row hash/index validation fails.
- Added generated CSV and minimal XLSX exports from canonical Parquet.
- Added a conservative `composite_v1` leaderboard that can require validation
  pass, exclude sandbox/current-universe rows, and rank by net costed results.
- Added `redx ledger append`, `redx ledger export`, and
  `redx ledger leaderboard`.
- Updated the ledger contract and marked `V2-AUD-LEDGER-001` as
  `self_checked`.
- No Lead Book, final validation, UI, paper/live behavior, order placement,
  sizing, runtime-mode change, candidate-pack writing, or promotion behavior
  was implemented.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_ledger_phase13.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Result:

- Focused Phase 13 tests passed: 8 passed.
- Full v2 tests passed: 97 passed.
- Contract-doc smoke passed: 2 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- Full `compileall` for `src\tradingbotsuite` passed.
- Contract tests passed: 462 passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
