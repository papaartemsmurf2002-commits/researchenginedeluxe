# V2-AUDIT-ID: V2-AUD-SEC-005
# V2-CONTRACTS: docs/contracts/security_boundary_contract.md
# V2-BOUNDARY: research_only, central_boundary_policy, no_live_imports
# V2-OWNER: v2_security
"""Central research-boundary policy for v2 artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY

BOUNDARY_TRUE_FIELDS = ("research_only", "observe_only")
BOUNDARY_FALSE_FIELDS = tuple(
    field for field, expected in RESEARCH_BOUNDARY.items() if expected is False
)
CANONICAL_BOUNDARY_FLAGS = MappingProxyType(dict(RESEARCH_BOUNDARY))


class ResearchBoundaryError(ValueError):
    """Raised when a v2 artifact violates the research-only boundary."""


def research_boundary_defaults() -> dict[str, bool]:
    return dict(CANONICAL_BOUNDARY_FLAGS)


def boundary_violation_reasons(
    payload: Mapping[str, Any] | object,
    *,
    require_all_fields: bool = True,
) -> tuple[str, ...]:
    reasons: list[str] = []
    for field, expected in CANONICAL_BOUNDARY_FLAGS.items():
        present, observed = _read_field(payload, field)
        if not present:
            if require_all_fields:
                reasons.append(f"{field}_missing")
            continue
        if bool(observed) is not expected:
            expected_label = "true" if expected else "false"
            reasons.append(f"{field}_must_be_{expected_label}")
    return tuple(reasons)


def require_research_boundary(
    payload: Mapping[str, Any] | object,
    *,
    context: str,
    require_all_fields: bool = True,
) -> None:
    reasons = boundary_violation_reasons(payload, require_all_fields=require_all_fields)
    if reasons:
        raise ResearchBoundaryError(
            f"{context} violates v2 research boundary: " + ",".join(reasons)
        )


def boundary_subset_payload(payload: Mapping[str, Any] | object) -> dict[str, bool | None]:
    values: dict[str, bool | None] = {}
    for field in CANONICAL_BOUNDARY_FLAGS:
        present, observed = _read_field(payload, field)
        values[field] = bool(observed) if present else None
    return values


def _read_field(payload: Mapping[str, Any] | object, field: str) -> tuple[bool, Any]:
    if isinstance(payload, Mapping):
        if field not in payload:
            return False, None
        return True, payload[field]
    if not hasattr(payload, field):
        return False, None
    return True, getattr(payload, field)
