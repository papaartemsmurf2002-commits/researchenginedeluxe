# WPR106-419 V2 Boundary P1 Fixes

Status: closed
Owner: Codex Manager Development Agent
Created: 2026-06-21

## Objective

Fix two P1 boundary issues found during the WPR106-418 baseline stabilization
audit before committing the v2 foundation as a baseline:

- official S3 backfill preservation must not copy arbitrary local files such
  as credentials, `.env`, local databases, or private caches into the archive;
- signal, position, and trade artifacts that carry signal or weight fields
  must include the full canonical v2 research-only invariant.

This packet does not run collectors against external services, run strategy
research, write generated research evidence outside test temp directories,
create candidate packs, place orders, produce paper/live signals, emit sizing
instructions, change runtime mode, or create promotion-ready artifacts.

## Audit IDs

- `V2-AUD-SEC-004`
- `V2-AUD-STRAT-003`
- `V2-AUD-BTENG-003`

## Allowed Paths

- `docs/work_packets/WPR106-419-v2-boundary-p1-fixes.md`
- `docs/KNOWN_ISSUES.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/archive/microstructure.py`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `src/tradingbotsuite/v2/strategy_specs/schemas.py`
- `src/tradingbotsuite/v2/backtest_engine/engine.py`
- `tests/v2/test_microstructure_collection_phase17.py`
- `tests/v2/test_strategy_specs_phase10.py`
- `tests/v2/test_backtest_engine_phase11.py`

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
- legacy GUI/web/operator paths
- `src/tradingbot/**`
- `.env`, credential files, local SQLite operator DBs, private caches

## Boundary Constraints

- Official-file preservation must require a trusted source root and must
  reject parent traversal, hidden/secret-like file names, credential-like file
  suffixes, and local-state database/cache files before writing archive output
  or manifest rows.
- Signal rows, signal frames, positions, and trades must include the canonical
  forbidden-output flags set to false.
- The fix must preserve research-only, observe-only, non-promotable semantics.
- No no-touch path may be edited.

## Acceptance Criteria

- Official S3 backfill jobs require `trusted_source_root`.
- `.env`, credential/key-like files, local SQLite database files, and escaped
  source paths fail before archive writes.
- `SignalRow` and `SignalFrame` carry and validate the full canonical
  invariant.
- `positions.parquet` and `trades.parquet` include the full canonical
  invariant columns with false forbidden flags.
- Focused tests pass for the changed v2 areas.

## Expected Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_microstructure_collection_phase17.py tests\v2\test_strategy_specs_phase10.py tests\v2\test_backtest_engine_phase11.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
py -3.11 -m compileall -q src\tradingbotsuite
git diff --check
```

Contract validation remains subject to `ISSUE-R106-026` in this Windows
session unless the socket state clears.

## Stop Conditions

- The fix requires touching live/runtime/order/sizing/promotion/candidate-pack
  paths.
- The official-file guard needs credential inspection beyond filename/path
  policy.
- Full invariant flags would be interpreted as paper/live/sizing/order/runtime
  authorization instead of explicit false boundary evidence.

## Completion Notes

Closed on 2026-06-21.

- Fixed `ISSUE-R106-027` by requiring official S3 backfill jobs to provide a
  `trusted_source_root`, resolving source files inside that root, and rejecting
  traversal plus secret/local-state file names before archive writes.
- Fixed `ISSUE-R106-028` by adding the full canonical research-only invariant
  to `SignalRow`, `SignalFrame`, vectorized backtest positions, and vectorized
  backtest trades.
- Added focused regressions for valid official-file preservation, rejected
  `.env`, credential, and traversal sources, compiled signal-frame invariant
  fields, forbidden signal-row flags, and Parquet positions/trades invariant
  columns.
- No live/runtime/order/sizing/promotion/candidate-pack paths were touched.
- No generated research evidence or checked legacy artifacts were rewritten.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_microstructure_collection_phase17.py tests\v2\test_strategy_specs_phase10.py tests\v2\test_backtest_engine_phase11.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Result:

- Focused v2 boundary tests passed: 28 passed.
- Full v2 tests passed: 173 passed.
- Python 3.11 compile passed.
- Contract tests passed in the default local Python environment: 462 passed.
- `git diff --check` passed with LF-to-CRLF warnings only.

Validation limitation:

- `py -3.11 -m pytest ...` could not run because the local Python 3.11
  interpreter has no `pytest` module installed. Final autonomous-ready
  certification still requires a pinned Python 3.11 test environment.
