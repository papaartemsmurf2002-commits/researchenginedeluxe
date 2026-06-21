# V2 Archive Contract

Status: v2 contract foundation
Audit IDs: `V2-AUD-CONTRACTS-001`, `V2-AUD-ARCH-001`, `V2-AUD-ARCH-005`

## Purpose

The archive owns market data provenance for v2. Backtests must read archive
snapshots through the backtest data service, not direct venue APIs.

## Initial Schema Names

- `ArchiveConfig`
- `ArchiveLayer`
- `ArchiveSnapshotRef`
- `ArchiveLayout`
- `IngestionRunRecord`
- `FileManifestRow`
- `ArchiveSnapshotRecord`
- `ArchiveValidationIssue`
- `RawJsonlZstdWriter`
- `ArchiveManifestStore`
- `BronzeCandleRow`
- `SilverBarRow`
- `BronzeFundingRow`
- `SilverFundingIntervalRow`
- `BronzeAssetContextRow`
- `SilverAssetContextRow`
- `NormalizationManifestRow`
- `NormalizationManifestStore`
- `MicrostructureDataType`
- `TradeEventRow`
- `BBOEventRow`
- `L2BookSnapshotRow`
- `MicrostructureQualityReport`
- `StorageBudgetReport`
- `RetentionBackupPolicyRecord`

## Required Rules

- Layers are `raw`, `bronze`, `silver`, and `gold`.
- Raw payloads and official files are immutable.
- Every file has SHA-256 identity, source venue, instrument ID, data family,
  time range, row count when applicable, and write timestamp.
- Snapshots are deterministic collections of manifest rows.
- Cleaning is allowed only in silver/gold layers and must record decisions.
- No silent repair, deletion, replacement, or unmanifested overwrite.
- Raw candle, funding, and asset-context payloads are parsed into bronze tables
  before silver normalization.
- Silver bar schema is stable:
  - `venue`
  - `instrument_id`
  - `timeframe`
  - `ts`
  - `end_ts`
  - `open`
  - `high`
  - `low`
  - `close`
  - `volume`
  - `trade_count`
  - `source_timeframe`
  - `source_file_id`
  - `source_layer`
  - `normalization_warnings`
  - research-boundary fields
- Derived 5m/15m/1h bars may be built from 1m bars only when each derived
  window is complete.
- Incomplete derived windows must be recorded in normalization manifests.
- Silver funding rows use explicit UTC interval start/end timestamps.
- Silver asset contexts normalize mark price, oracle price, open interest,
  daily notional volume, and funding rate fields.
- Archive path partitions must be safe on Windows and POSIX; v2 instrument IDs
  containing namespace separators are encoded in paths while manifest fields
  preserve the original ID.
- Trades, BBO, and L2 fixture captures must be preserved as raw archive files
  before any later bronze/silver interpretation.
- Microstructure raw rows must carry event type, instrument, UTC timestamp,
  sequence, research-only boundary fields, and a datatype-specific minimum
  schema.
- Official S3-style backfill files must be copied into the raw archive in their
  native file format and recorded in `file_manifest` plus ingestion-run
  manifests.
- Microstructure quality reports must expose row counts, event windows, gaps,
  reconnect evidence, and warning status for trades, BBO, and L2 captures.
- Storage budget reports must make archive growth visible by total bytes, layer
  bytes, largest files, and budget status.
- Retention and backup policy records are record-only evidence in this phase;
  they must not authorize deletion, movement, upload, or overwrite behavior.

## Forbidden

- Direct backtest API pulls.
- Promotion-ready archive outputs.
- Archive mutation from strategy code.
- Treating bronze/silver rebuilds as accepted backtest reads without the Phase 9
  backtest data service gates.
- Treating raw microstructure captures or official-file backfills as live
  execution proof, paper trading evidence, order readiness, or promotion-ready
  evidence.
- Applying retention/backup policy records by deleting, moving, or uploading
  archive files in this branch phase.
