# WPR106-438 - V2 Universe Snapshot Coverage Audit Worker

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-QUAL-005`
- `V2-AUD-WORKER-011`
- `V2-AUD-ARCH-015`
- `V2-AUD-UNIV-004`

## Objective

Extend the durable `coverage_audit` worker so it can audit a silver archive
snapshot against a Hyperliquid universe snapshot, not only one silver bars file.
The job must emit coverage and quality manifests for every eligible universe
instrument in scope, surface missing archive files and low coverage as blocker
evidence, and preserve the existing single-file coverage-audit mode.

This packet moves the v2 operational loop from per-file diagnostics toward:

```text
universe snapshot -> archive snapshot -> coverage/quality audit -> blockers
```

It does not create accepted research evidence, autonomous-ready status,
strategy output, candidate-pack output, paper/live/order/sizing/runtime behavior,
or promotion behavior.

## Allowed Paths

- `docs/work_packets/WPR106-438-v2-universe-snapshot-coverage-audit.md`
- `docs/contracts/data_quality_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/data_quality/jobs.py`
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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py -q
```

Baseline:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
git diff --check
```

## Implementation Notes

- Keep the existing `file_id`/`silver_file_id` coverage audit path unchanged.
- Add a second mode selected by `archive_snapshot_id` plus
  `universe_snapshot_id`.
- Read only local archive manifests, universe manifests, and silver bar Parquet
  files; do not call venue APIs.
- Default the universe sweep to eligible instruments only.
- Treat missing silver bars for eligible instruments as coverage blocker
  evidence by writing zero-observed coverage reports, not as a worker-system
  failure.
- Return compact summary refs: report IDs, quality-check IDs, eligible count,
  audited count, missing-file instruments, minimum coverage, evidence-eligible
  count, blocked count, and blocker reasons.

## Decisions Made

- Added universe-snapshot coverage audit as a second mode on the existing
  durable `coverage_audit` worker, selected by `archive_snapshot_id` plus
  `universe_snapshot_id`.
- Preserved the existing single-file `file_id`/`silver_file_id` mode and made
  mixed single-file plus snapshot specs fail closed.
- Defaulted snapshot sweeps to eligible universe rows only. Excluded
  instruments remain out of scope unless a later packet explicitly changes the
  policy.
- Missing eligible instrument silver bars are represented as zero-observed
  coverage reports plus `missing_silver_bars_file` worker refs. They are
  blocker evidence, not worker-system failures.
- Accepted the explorer sidecar recommendation that bounded public candle
  pagination remains the next collector-focused follow-up, but kept this packet
  on coverage because it closes the current universe -> archive -> coverage
  audit link without changing venue access.

## Changed Files

- `docs/work_packets/WPR106-438-v2-universe-snapshot-coverage-audit.md`
- `docs/contracts/data_quality_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/data_quality/jobs.py`
- `tests/v2/test_workers_phase7.py`

## Acceptance Evidence

- Focused worker validation:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py -q`
  - Result: `34 passed`
- Compile:
  - `python -m compileall -q src/tradingbotsuite`
  - Result: passed
- Contracts:
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  - Result: `463 passed`
- Full v2 suite:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  - Result: `225 passed`
- Diff hygiene:
  - `git diff --check`
  - Result: passed with existing LF-to-CRLF warnings only.

## No-Touch Review

- No no-touch path was edited.
- No live runtime, order-placement, sizing, runtime config, promotion,
  candidate-pack truth-layer, legacy GUI, checked `data/research/**` evidence,
  secret, credential, local DB, or private cache path was touched.
- The worker reads only local archive manifests, universe manifests, and silver
  bar Parquet files in the new mode. It performs no venue/API fetch.
- The packet adds no accepted-evidence, autonomous-ready, candidate-ready,
  paper/live/order/sizing/runtime, or promotion behavior.
