# V2-AUDIT-ID: V2-AUD-ARCHINV-001
# V2-CONTRACTS: docs/contracts/backtest_data_service_contract.md, docs/contracts/validation_contract.md
# V2-BOUNDARY: research_only, archive_inventory, no_live_imports, no_archive_writes
# V2-OWNER: v2_archive_inventory
"""Archive inventory and strategy data-requirement resolver."""

from tradingbotsuite.v2.archive_inventory.schemas import (
    ArchiveInventory,
    ArchiveInventoryRecord,
    ArchiveInventorySummary,
    ArtifactMode,
    BenchmarkObservation,
    DataGapRequest,
    FastLaneExecutionPolicy,
    StrategyDataRequirementReport,
    StrategyDataRequirementRequest,
)
from tradingbotsuite.v2.archive_inventory.service import (
    ArchiveInventoryError,
    ArchiveInventoryService,
)
from tradingbotsuite.v2.archive_inventory.snapshot_bridge import (
    CentralArchiveSnapshotBridgeConfig,
    CentralArchiveSnapshotBridgeError,
    CentralArchiveSnapshotBridgeResult,
    build_central_archive_snapshot_bridge,
)

__all__ = [
    "ArchiveInventory",
    "ArchiveInventoryError",
    "ArchiveInventoryRecord",
    "ArchiveInventoryService",
    "ArchiveInventorySummary",
    "ArtifactMode",
    "BenchmarkObservation",
    "CentralArchiveSnapshotBridgeConfig",
    "CentralArchiveSnapshotBridgeError",
    "CentralArchiveSnapshotBridgeResult",
    "DataGapRequest",
    "FastLaneExecutionPolicy",
    "StrategyDataRequirementReport",
    "StrategyDataRequirementRequest",
    "build_central_archive_snapshot_bridge",
]
