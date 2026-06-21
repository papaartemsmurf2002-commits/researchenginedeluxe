# V2-AUDIT-ID: V2-AUD-ARCH-004
# V2-CONTRACTS: docs/contracts/archive_contract.md
# V2-BOUNDARY: research_only, archive_manifests, no_live_imports
# V2-OWNER: v2_archive
"""V2 archive bounded context."""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "ArchiveLayer",
    "ArchiveLayout",
    "ArchiveManifestStore",
    "BBOEventRow",
    "BronzeAssetContextRow",
    "BronzeCandleRow",
    "BronzeFundingRow",
    "L2BookSnapshotRow",
    "MicrostructureDataType",
    "NormalizationManifestRow",
    "RawJsonlZstdWriter",
    "RetentionBackupPolicyRecord",
    "StorageBudgetReport",
    "SilverAssetContextRow",
    "SilverBarRow",
    "SilverFundingIntervalRow",
    "TradeEventRow",
    "bronze_asset_contexts_to_silver",
    "bronze_candles_to_silver_bars",
    "bronze_funding_to_silver",
    "build_retention_backup_policy",
    "build_storage_budget_report",
    "normalize_microstructure_rows",
    "raw_asset_contexts_to_bronze",
    "raw_candles_to_bronze",
    "raw_funding_to_bronze",
    "record_retention_backup_policy",
    "write_microstructure_raw_capture",
]

_EXPORT_MODULES = {
    "ArchiveLayer": "tradingbotsuite.v2.archive.schemas",
    "ArchiveLayout": "tradingbotsuite.v2.archive.layout",
    "ArchiveManifestStore": "tradingbotsuite.v2.archive.manifest_store",
    "BBOEventRow": "tradingbotsuite.v2.archive.microstructure",
    "BronzeAssetContextRow": "tradingbotsuite.v2.archive.market_data",
    "BronzeCandleRow": "tradingbotsuite.v2.archive.market_data",
    "BronzeFundingRow": "tradingbotsuite.v2.archive.market_data",
    "L2BookSnapshotRow": "tradingbotsuite.v2.archive.microstructure",
    "MicrostructureDataType": "tradingbotsuite.v2.archive.microstructure",
    "NormalizationManifestRow": "tradingbotsuite.v2.archive.market_data",
    "RawJsonlZstdWriter": "tradingbotsuite.v2.archive.raw_writer",
    "RetentionBackupPolicyRecord": "tradingbotsuite.v2.archive.microstructure",
    "StorageBudgetReport": "tradingbotsuite.v2.archive.microstructure",
    "SilverAssetContextRow": "tradingbotsuite.v2.archive.market_data",
    "SilverBarRow": "tradingbotsuite.v2.archive.market_data",
    "SilverFundingIntervalRow": "tradingbotsuite.v2.archive.market_data",
    "TradeEventRow": "tradingbotsuite.v2.archive.microstructure",
    "bronze_asset_contexts_to_silver": "tradingbotsuite.v2.archive.rebuild",
    "bronze_candles_to_silver_bars": "tradingbotsuite.v2.archive.rebuild",
    "bronze_funding_to_silver": "tradingbotsuite.v2.archive.rebuild",
    "build_retention_backup_policy": "tradingbotsuite.v2.archive.microstructure",
    "build_storage_budget_report": "tradingbotsuite.v2.archive.microstructure",
    "normalize_microstructure_rows": "tradingbotsuite.v2.archive.microstructure",
    "raw_asset_contexts_to_bronze": "tradingbotsuite.v2.archive.rebuild",
    "raw_candles_to_bronze": "tradingbotsuite.v2.archive.rebuild",
    "raw_funding_to_bronze": "tradingbotsuite.v2.archive.rebuild",
    "record_retention_backup_policy": "tradingbotsuite.v2.archive.microstructure",
    "write_microstructure_raw_capture": "tradingbotsuite.v2.archive.microstructure",
}


def __getattr__(name: str):
    module_name = _EXPORT_MODULES.get(name)
    if module_name is not None:
        value = getattr(import_module(module_name), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
