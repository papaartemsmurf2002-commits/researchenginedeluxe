# V2-AUDIT-ID: V2-AUD-UI-001
# V2-CONTRACTS: docs/contracts/ui_visibility_contract.md
# V2-BOUNDARY: research_only, read_only_visibility, no_live_imports
# V2-OWNER: v2_ui
"""Read-only v2 visibility UI helpers."""

from __future__ import annotations

from tradingbotsuite.v2.ui.render import (
    render_visibility_html,
    write_visibility_html,
)
from tradingbotsuite.v2.ui.schemas import (
    ArchiveCoverageRow,
    AuditChunkVisibilityRow,
    CollectionStatusRow,
    DeepValidationVisibilityRow,
    FinalHardTestVisibilityRow,
    GapReportRow,
    LeadBookVisibilityRow,
    LockboxVisibility,
    UniverseVisibilityRow,
    V2VisibilitySnapshot,
    WorkerJobVisibilityRow,
    snapshot_from_json,
    snapshot_from_mapping,
)

__all__ = [
    "ArchiveCoverageRow",
    "AuditChunkVisibilityRow",
    "CollectionStatusRow",
    "DeepValidationVisibilityRow",
    "FinalHardTestVisibilityRow",
    "GapReportRow",
    "LeadBookVisibilityRow",
    "LockboxVisibility",
    "UniverseVisibilityRow",
    "V2VisibilitySnapshot",
    "WorkerJobVisibilityRow",
    "render_visibility_html",
    "snapshot_from_json",
    "snapshot_from_mapping",
    "write_visibility_html",
]
