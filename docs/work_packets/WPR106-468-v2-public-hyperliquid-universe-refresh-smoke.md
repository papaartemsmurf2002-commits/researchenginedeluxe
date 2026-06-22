# WPR106-468 - V2 Public Hyperliquid Universe Refresh Smoke

Status: self_checked
Audit ID: `V2-AUD-UNIV-005`
Related audit IDs: `V2-AUD-XVENUE-015`, `V2-AUD-ARCH-026`

## Objective

Run a bounded local operational smoke of `redx universe refresh` against the
public Hyperliquid info endpoint, writing output only under an ignored local
`data/research/wpr106_468_public_hyperliquid_universe_refresh/` path. This
packet records whether public universe refresh is operational in this session
without committing venue payloads, weakening as-of/current-universe labeling,
or claiming accepted/autonomous/candidate/paper/live/sizing/runtime/promotion
readiness.

## Allowed Paths

- `docs/work_packets/WPR106-468-v2-public-hyperliquid-universe-refresh-smoke.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- ignored local generated evidence under
  `data/research/wpr106_468_public_hyperliquid_universe_refresh/**`

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

Operational smoke:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.v2.cli.main universe refresh --archive-root data/research/wpr106_468_public_hyperliquid_universe_refresh/archive --venue hyperliquid --min-day-notional-usd 5000000 --source public_api --asof-date 2026-06-22 --mode current_labeled_sandbox --include-hip3-dexs
```

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_universe_phase5.py -q
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
git diff --check
```

## Planned Changed Files

- `docs/work_packets/WPR106-468-v2-public-hyperliquid-universe-refresh-smoke.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Changed Files

- `docs/work_packets/WPR106-468-v2-public-hyperliquid-universe-refresh-smoke.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- Ignored local operational evidence under
  `data/research/wpr106_468_public_hyperliquid_universe_refresh/**`

## Decisions Made

- Public API output is local operational evidence only and stays ignored by
  git. This avoids committing venue payloads or making data-licensing claims in
  this packet.
- The run uses `current_labeled_sandbox` because a current public endpoint is
  not an as-of historical universe source.
- Any network failure is recorded as an operational blocker, not a source-code
  failure.

## Acceptance Evidence

Operational smoke command completed successfully on 2026-06-22:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.v2.cli.main universe refresh --archive-root data/research/wpr106_468_public_hyperliquid_universe_refresh/archive --venue hyperliquid --min-day-notional-usd 5000000 --source public_api --asof-date 2026-06-22 --mode current_labeled_sandbox --include-hip3-dexs
```

Observed CLI evidence:

- `universe_snapshot_id=f8d227bf1960d5b0bee7d9b189a2abf447d380f3dc93b471976f84ca400fb609`
- `raw_file_id=2ee1381738f63f9d5fb080fd73a1aadf963f28b075ac1542b1f90128dae68d9b`
- `raw_payload_sha256=38d30d1740de2196537c9129e7526a61a372e021e36520486b325296300bc49e`
- `venue_adapter_id=hyperliquid_public_info_v1`
- `source_endpoint_or_subscription=info/metaAndAssetCtxs`
- `raw_request_id=554ed321869d2075b03bd823a75cd5f7b8e91520813b01973caa485980241afa`
- `raw_response_id=5bbbad20753ab727b427e40e558f2196ec661b79e585fb5f344bd2e96803ccb6`
- `instrument_count=230`
- `eligible_count=26`
- `universe_mode=current_labeled_sandbox`

Generated local evidence files are ignored by git:

- `archive/raw/venue=hyperliquid/datatype=meta_and_asset_ctxs/date=2026-06-22/run_id=universe-2026-06-22-38d30d1740de2196/meta_and_asset_ctxs.jsonl.zst`
- `archive/manifests/file_manifest.parquet`
- `archive/manifests/ingestion_runs.parquet`
- `archive/manifests/instrument_catalog.parquet`
- `archive/manifests/asset_context_snapshots.parquet`
- `archive/manifests/universe_snapshots.parquet`

Manifest checks:

- `universe_snapshots.parquet` rows: 230
- `instrument_catalog.parquet` rows: 230
- `asset_context_snapshots.parquet` rows: 230
- Eligible rows: 26
- Ineligible rows: 204, all `volume_below_threshold`
- Evidence scope: `current_sandbox_only`
- `accepted_research_evidence_allowed=False`

Validation:

- `tests/v2/test_universe_phase5.py -q`: 19 passed.
- `python -m compileall -q src/tradingbotsuite`: passed.
- `git diff --check`: passed with existing LF-to-CRLF warnings on touched docs
  only.
