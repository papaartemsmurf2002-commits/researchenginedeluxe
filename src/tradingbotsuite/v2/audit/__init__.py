# V2-AUDIT-ID: V2-AUD-PKG-001
# V2-CONTRACTS: docs/PRODUCT_SCOPE.md, docs/audit/V2_AUDIT_INDEX.md
# V2-BOUNDARY: research_only, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_audit
"""V2 audit package."""

from __future__ import annotations

from tradingbotsuite.v2.audit.schemas import (
    AuditBlockerReport,
    AuditJobSummary,
    AuditReportStatus,
)
from tradingbotsuite.v2.audit.markers import V2ModuleMarker, module_marker
from tradingbotsuite.v2.audit.readiness import (
    AutonomousReadinessEvidence,
    AutonomousReadinessReport,
    AutonomousReadinessStatus,
    ReadinessCheckSummary,
    ReadinessEvidenceItem,
    REQUIRED_AUTONOMOUS_READINESS_KEYS,
    load_autonomous_readiness_evidence,
    run_autonomous_readiness_audit,
    run_autonomous_readiness_audit_from_file,
)

__all__ = [
    "AuditBlockerReport",
    "AuditJobSummary",
    "AuditReportStatus",
    "AutonomousReadinessEvidence",
    "AutonomousReadinessReport",
    "AutonomousReadinessStatus",
    "ReadinessCheckSummary",
    "ReadinessEvidenceItem",
    "REQUIRED_AUTONOMOUS_READINESS_KEYS",
    "V2ModuleMarker",
    "load_autonomous_readiness_evidence",
    "module_marker",
    "run_autonomous_readiness_audit",
    "run_autonomous_readiness_audit_from_file",
]
