# V2 Operations Runbook

Status: Phase 7 initial runbook
Source: `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`

This runbook is for local research-only v2 operations. It does not authorize
paper trading, live trading, order placement, sizing, runtime-mode changes,
candidate packs, or promotion artifacts.

## Initialize Archive

```powershell
$env:PYTHONPATH='src'
python -m tradingbotsuite.v2.cli.main archive init --archive-root data/archive
```

The archive root owns raw, bronze, silver, gold, manifest, performance, and
Lead Book directories. Checked tests should use temporary archive roots.

## Initialize Job Store

```powershell
$env:PYTHONPATH='src'
python -m tradingbotsuite.v2.cli.main worker init --job-store data/jobs/redx_jobs.sqlite
```

The first durable local store is SQLite in WAL mode. Job rows store metadata
only; market data and research artifacts remain in archive or artifact paths.

## Start Collectors

Queue jobs first, then run workers from a process outside the ASGI/operator
request path.

Repeatable local payload-file refresh:

```powershell
python -m tradingbotsuite.v2.cli.main worker enqueue `
  --job-store data/jobs/redx_jobs.sqlite `
  --kind universe_refresh `
  --input-spec-file specs/jobs/universe_refresh.json

python -m tradingbotsuite.v2.cli.main worker run `
  --job-store data/jobs/redx_jobs.sqlite `
  --kind universe_refresh `
  --worker-id local-universe-worker-1
```

The `universe_refresh` input spec must declare either:

```json
{
  "archive_root": "data/archive",
  "source": "payload_file",
  "payload_file": "specs/fixtures/hyperliquid_meta_and_asset_ctxs.json",
  "asof_date": "2026-06-21",
  "min_day_notional_usd": 5000000
}
```

or the explicit unsigned public metadata mode:

```json
{
  "archive_root": "data/archive",
  "source": "public_api",
  "public_info_url": "https://api.hyperliquid.xyz/info",
  "public_info_timeout": 20,
  "asof_date": "2026-06-21",
  "min_day_notional_usd": 5000000
}
```

Public API universe refreshes call only the unsigned Hyperliquid `/info`
`metaAndAssetCtxs` endpoint. The resulting worker refs include `source_mode`,
raw payload hash, venue adapter ID, source endpoint, and raw request/response
IDs. They prove public universe metadata intake only; they do not prove market
data coverage, accepted backtest evidence, autonomous-ready status, or any
paper/live/order/sizing/runtime/promotion capability.

Use `--forbid-asgi` in service integration tests to prove worker code is not
being executed inside the operator process.

## Inspect Job Health

```powershell
python -m tradingbotsuite.v2.cli.main worker status --job-store data/jobs/redx_jobs.sqlite
python -m tradingbotsuite.v2.cli.main worker mark-stale --job-store data/jobs/redx_jobs.sqlite --stale-after-seconds 300
```

Stale heartbeats are evidence. Do not silently reclaim them without a transition
record.

## Backfill Gaps

Phase 7 records reconnect/gap evidence. Later Phase 8+ backfills should queue
explicit backfill jobs that reference the gap record ID, archive snapshot, venue,
instrument, datatype, timeframe, and time window.

## Stop Workers Safely

Stop after the active job finishes when possible. If a process exits mid-job,
the next health check should mark the job `stale`; an operator can inspect and
then run:

```powershell
python -m tradingbotsuite.v2.cli.main worker retry --job-store data/jobs/redx_jobs.sqlite --job-id JOB-...
```

## Rebuild Bronze And Silver

Bronze/silver rebuilds write manifest rows and normalization manifests. Use
local raw/bronze file IDs from `file_manifest.parquet`.

```powershell
python -m tradingbotsuite.v2.cli.main archive build-bronze `
  --archive-root data/archive `
  --raw-file-id RAW_FILE_ID `
  --datatype candles `
  --job-id JOB-bronze-candles

python -m tradingbotsuite.v2.cli.main archive build-silver `
  --archive-root data/archive `
  --bronze-file-id BRONZE_FILE_ID `
  --datatype candles `
  --job-id JOB-silver-bars `
  --derive-timeframes 5m,15m,1h `
  --snapshot
```

Supported Phase 8 datatypes are `candles`, `funding`, and `asset_contexts`.
Derived bars are written only for complete windows; incomplete windows are
normalization evidence, not silent repairs.

## Snapshot Archive

```powershell
python -m tradingbotsuite.v2.cli.main archive snapshot `
  --archive-root data/archive `
  --layer silver `
  --venue-scope hyperliquid `
  --start-ts 2026-01-01T00:00:00+00:00 `
  --end-ts 2026-02-01T00:00:00+00:00
```

Snapshots are research evidence inputs only.

## Run A Safe Backtest

Backtest execution is future Phase 10+ work. When enabled, it must read through
the backtest data service, enforce lockbox/coverage/as-of-universe gates, run
outside the ASGI/operator process, and write durable job transitions.

## Append Ledger

Ledger append/export is future Phase 13 work. Failed trials must be logged;
XLSX exports must be generated views only.

## Export XLSX

Use only the future ledger export command after the append-only ledger exists.
Do not manually edit spreadsheet output as source of truth.

## Audit A Chunk

Every chunk needs an audit ID, work packet, bounded paths, tests, validation
commands, and audit-index status update. Use:

- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/audit/prompts/V2_CHUNK_AUDITOR_PROMPT.md`
- the chunk work packet under `docs/work_packets/`

## Recover From Corrupted Partial Files

Do not silently delete or overwrite evidence. Record the failing job, affected
manifest refs, file paths, hashes if available, and the recovery action in the
work packet or `docs/KNOWN_ISSUES.md` if blocking. Re-run through a durable job
so the replacement has transition and manifest evidence.
