# V2-AUDIT-ID: V2-AUD-PKG-001
# V2-CONTRACTS: docs/PRODUCT_SCOPE.md, docs/audit/V2_AUDIT_INDEX.md
# V2-BOUNDARY: research_only, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_audit
"""Audit marker helper for v2 modules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class V2ModuleMarker:
    audit_id: str
    contracts: tuple[str, ...]
    boundary: tuple[str, ...]
    owner: str


def module_marker(
    *,
    audit_id: str,
    contracts: tuple[str, ...],
    boundary: tuple[str, ...],
    owner: str,
) -> V2ModuleMarker:
    return V2ModuleMarker(
        audit_id=audit_id,
        contracts=contracts,
        boundary=boundary,
        owner=owner,
    )
