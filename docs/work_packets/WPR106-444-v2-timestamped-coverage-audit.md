# WPR106-444 - V2 Timestamped Non-Bar Coverage Audit

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-QUAL-006`
- `V2-AUD-ARCH-021`

## Objective

Add bounded coverage-audit support for timestamped non-bar archive rows so
raw `trades`, raw `bbo`, raw `l2`, and silver `asset_contexts` files can
produce explicit coverage reports. The audit must measure nonempty timestamp
buckets over a declared `[start_ts, end_ts)` window and bucket timeframe,
surface missing buckets and missing per-instrument files, and label this as
coverage measurement rather than proof of event completeness, queue/fill
realism, or accepted research readiness.

This packet does not fetch venue data, create new collector modes, normalize
microstructure into bronze/silver, change coverage floors, change date floors,
change lockbox policy, alter candidate/promotion language, or add paper/live/
order/sizing/runtime behavior.

## Allowed Paths

- `docs/work_packets/WPR106-444-v2-timestamped-coverage-audit.md`
- `docs/contracts/data_quality_contract.md`
- `docs/contracts/archive_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/data_quality/coverage.py`
- `src/tradingbotsuite/v2/data_quality/jobs.py`
- `tests/v2/test_data_quality_phase6.py`
- `tests/v2/test_workers_phase7.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, or
  candidate-pack truth-layer paths.
- No legacy GUI paths.
- No checked historical evidence under `data/research/**`.
- No secrets, `.env`, local SQLite operator DBs, private cache, or generated
  runtime output paths.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_data_quality_phase6.py tests/v2/test_workers_phase7.py -q
```

Baseline:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
git diff --check
```

## Implementation Notes

- Add a deterministic timestamp-bucket coverage helper for non-bar rows.
- Use existing coverage report schema fields; do not weaken the default
  `0.98` accepted-evidence coverage floor.
- Count unique nonempty buckets rather than event rows so repeated events do
  not inflate coverage.
- Treat duplicated event keys as blocker evidence when the source row provides
  a sequence field.
- Wire `coverage_audit` workers to support:
  - direct raw `trades`, `bbo`, or `l2` file IDs;
  - direct silver `asset_contexts` file IDs;
  - archive-snapshot plus universe-snapshot audits for those same timestamped
    families.
- Keep existing silver-bar coverage behavior unchanged.

## Decisions Made

- Added `coverage_report_for_timestamped_rows` for non-bar archive rows. It
  measures unique nonempty time buckets over a declared `[start_ts, end_ts)`
  window and timeframe rather than counting event rows.
- Kept existing silver-bar coverage behavior unchanged.
- Wired direct `coverage_audit` file jobs for raw `trades`, raw `bbo`, raw
  `l2`, and silver `asset_contexts` manifest rows.
- Wired archive-snapshot plus universe-snapshot coverage jobs for the same
  timestamped families, with missing per-instrument files surfaced as blocker
  evidence.
- Kept raw microstructure coverage non-evidence by default with
  `raw_microstructure_not_accepted_coverage_evidence`, even when a caller asks
  for `accepted_research` mode.
- Allowed silver `asset_contexts` coverage to use the normal coverage gate
  because those rows are already silver archive data, while still relying on
  missing-bucket and missing-file blocker evidence.
- Did not add fetching, collector modes, bronze/silver microstructure
  normalization, queue/fill realism, accepted continuous historical proof,
  coverage-floor changes, date-floor changes, lockbox changes, or
  paper/live/order/sizing/runtime/promotion behavior.

## Changed Files

- `docs/work_packets/WPR106-444-v2-timestamped-coverage-audit.md`
- `docs/contracts/data_quality_contract.md`
- `docs/contracts/archive_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/data_quality/coverage.py`
- `src/tradingbotsuite/v2/data_quality/jobs.py`
- `tests/v2/test_data_quality_phase6.py`
- `tests/v2/test_workers_phase7.py`

## Acceptance Evidence

- Focused validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_data_quality_phase6.py tests/v2/test_workers_phase7.py -q`
  passed with 48 tests.
- Compile validation:
  `$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite` passed.
  A first compile attempt without `PYTHONPATH` failed before compilation with a
  transient local Python process-launch error, then the standard validation
  command passed.
- Contract validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed with
  463 tests.
- Full v2 validation:
  `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q` passed with 247 tests.
- Diff hygiene:
  `git diff --check` passed with line-ending warnings only.

## No-Touch Review

- No live runtime, order-placement, sizing, runtime config, promotion,
  candidate-pack truth-layer, legacy GUI, checked historical evidence, secret,
  `.env`, local SQLite operator DB, private cache, or generated runtime output
  path was changed.
- No research artifact was marked autonomous-ready, candidate-ready,
  promotion-ready, paper-ready, live-ready, order-ready, sizing-ready,
  signal-ready, or accepted continuous historical microstructure evidence.
